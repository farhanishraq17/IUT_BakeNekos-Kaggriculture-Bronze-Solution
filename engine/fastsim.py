"""Fast Kaggriculture runner.

Parity by construction: this does NOT reimplement the rules. It calls the pinned
reference interpreter (`kaggriculture_ref.py`) directly, and only strips the
kaggle-environments wrapper around it (jsonschema validation, per-step deepcopy
of every observation, Struct boxing). That wrapper is where the time goes.

Agents receive plain dicts. By default they share the live state objects, so an
agent that MUTATES its observation will corrupt the game -- pass copy=True when
running untrusted opponents.
"""

from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

_REF = Path(__file__).with_name("kaggriculture_ref.py")


def _load_ref():
    """Exec the pinned engine with its one kaggle_environments import stripped.

    Importing the real package costs seconds (it enumerates every env on disk),
    which dwarfs a 140 ms game and makes worker startup the bottleneck. The only
    thing the engine needs from it is `resolve_episode_seed`, which we supply."""
    src = _REF.read_text(encoding="utf-8").replace(
        "from kaggle_environments.utils import resolve_episode_seed", "", 1)
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("kaggriculture_ref", loader=None))
    mod.__file__ = str(_REF)
    mod.resolve_episode_seed = _resolve_seed
    exec(compile(src, str(_REF), "exec"), mod.__dict__)
    sys.modules.setdefault("kaggriculture_ref", mod)
    return mod


def _resolve_seed(env, *, config_key="seed", fallback=None):
    """Same contract as kaggle_environments.utils.resolve_episode_seed."""
    import random
    if getattr(env, "info", None) is None:
        env.info = {}
    seed = env.info.get("seed")
    if seed is None:
        seed = env.configuration.get(config_key)
    if seed is None:
        seed = fallback() if fallback else random.randrange(2 ** 31)
    seed = int(seed)
    env.configuration.pop(config_key, None)
    env.info["seed"] = seed
    return seed


REF = _load_ref()

DEFAULTS = {
    "episodeSteps": 720,
    "actTimeout": 1,
    "boardSize": 10,
    "startingMoney": 3000,
    "maxMarketOrdersPerTurn": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "weedSpawnChance": 0.005,
    "townShopUnlockInterval": 3,
    "townShopSellInterval": 4,
    "townCenterSellInterval": 24,
    "farmHandCostMult": 1,
    "marketParams": {},
    "seed": None,
}

PASS = {"farmer": ["PASS"], "hands": [], "market": []}


class _Cfg(dict):
    """The reference interpreter reads `cfg.episodeSteps` as an attribute."""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e


class _Obs:
    """Attribute-access observation; the reference interpreter uses getattr on it."""

    __slots__ = ("player", "private", "farms", "market", "town", "day", "hour", "step")

    def __init__(self):
        for s in self.__slots__:
            setattr(self, s, None)

    def as_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


class _St:
    __slots__ = ("observation", "action", "status", "reward")

    def __init__(self):
        self.observation = _Obs()
        self.action = None
        self.status = "ACTIVE"
        self.reward = 0.0


class _Env:
    __slots__ = ("configuration", "info", "done")

    def __init__(self, configuration, info):
        self.configuration = configuration
        self.info = info
        self.done = False


class Game:
    """One episode. `step(actions)` advances a turn; `obs(i)` is agent i's view."""

    def __init__(self, seed: int | None = None, configuration: dict | None = None, copy: bool = False):
        cfg = _Cfg(DEFAULTS)
        if configuration:
            cfg.update(configuration)
        if seed is not None:
            cfg["seed"] = int(seed)
        self.copy = copy
        self.env = _Env(cfg, {})
        self.state = [_St(), _St()]
        REF._initialize(self.state, self.env)
        self.step_n = 0
        self._sync_step()

    def _sync_step(self):
        for s in self.state:
            s.observation.step = self.step_n

    @property
    def done(self) -> bool:
        return self.state[0].status != "ACTIVE"

    @property
    def money(self) -> list[float]:
        return [f["money"] for f in self.state[0].observation.farms]

    def obs(self, player: int) -> dict:
        d = self.state[player].observation.as_dict()
        return deepcopy(d) if self.copy else d

    def step(self, actions) -> None:
        for s, a in zip(self.state, actions):
            s.action = a if isinstance(a, dict) else PASS
        REF.interpreter(self.state, self.env)
        self.step_n += 1
        self._sync_step()

    def rewards(self) -> list[float]:
        return [float(s.reward) for s in self.state]


def _takes_config(fn) -> bool:
    import inspect
    try:
        params = [p for p in inspect.signature(fn).parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.VAR_POSITIONAL)]
    except (TypeError, ValueError):
        return False
    return len(params) >= 2 or any(p.kind == p.VAR_POSITIONAL for p in params)


def run(agent0, agent1, seed: int | None = None, configuration: dict | None = None,
        copy: bool = False) -> list[float]:
    """Play a full episode. Returns final money per player.

    An agent that raises is treated as PASS for that turn (the real runner would
    mark it errored and it would lose -- we surface it via `run.errors` instead of
    aborting, so a crashy opponent does not kill an optimization batch)."""
    g = Game(seed, configuration, copy)
    agents = (agent0, agent1)
    # Kaggle's runner passes (observation, configuration) to any agent that takes a
    # second positional argument -- some public agents declare `agent(obs, config)`
    # with no default and would raise on every turn if we only passed obs.
    cfg = g.env.configuration
    two = [_takes_config(fn) for fn in agents]
    errors = [0, 0]
    steps = g.env.configuration["episodeSteps"]
    for _ in range(steps - 1):
        acts = []
        for i, fn in enumerate(agents):
            try:
                acts.append(fn(g.obs(i), cfg) if two[i] else fn(g.obs(i)))
            except Exception:
                errors[i] += 1
                acts.append(PASS)
        g.step(acts)
        if g.done:
            break
    run.errors = errors
    run.shops = list(g.state[0].observation.town["unlocked_shops"])
    return g.money


run.errors = [0, 0]
run.shops = []


def duel(agent_a, agent_b, seeds, configuration=None, copy=False) -> dict:
    """Paired match: every seed played from both seats. Rating ignores margin,
    so the headline number is win rate, not cash."""
    wins = losses = ties = 0
    margin = 0.0
    for s in seeds:
        for swap in (False, True):
            m = run(agent_b, agent_a, s, configuration, copy) if swap else \
                run(agent_a, agent_b, s, configuration, copy)
            a, b = (m[1], m[0]) if swap else (m[0], m[1])
            margin += a - b
            if a > b:
                wins += 1
            elif a < b:
                losses += 1
            else:
                ties += 1
    n = max(1, wins + losses + ties)
    return {
        "w": wins, "l": losses, "t": ties, "n": n,
        "win_rate": (wins + 0.5 * ties) / n,
        "mean_margin": margin / n,
    }


if __name__ == "__main__":
    import time
    from kaggriculture_ref import starter_agent, pass_agent  # noqa: F401  (same module object)

    t0 = time.time()
    m = run(REF.starter_agent, REF.pass_agent, seed=1)
    dt = time.time() - t0
    print(f"starter vs pass, seed 1 -> {m}   {dt*1000:.0f} ms/game  ({1/dt:.1f} games/s)")
    assert m[0] > m[1], "starter should beat pass"
    print("ok")
