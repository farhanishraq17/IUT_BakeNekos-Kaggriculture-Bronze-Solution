"""Gate: fastsim must be indistinguishable from the official kaggle-environments runner.

Run after ANY change to fastsim.py or the engine.  A fast sim that has drifted is
worse than no fast sim -- every optimization result downstream becomes fiction.

    python engine/test_parity.py [n_seeds]
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fastsim  # noqa: E402

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
UNIT_OPS = ["NORTH", "SOUTH", "EAST", "WEST", "PASS", "WATER", "HARVEST", "DIG",
            "BUILD_COOP", "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER", "DROP"]


def noisy_agent(obs):
    """Deterministic given (player, step): exercises every engine code path without
    depending on how the host boxes the observation."""
    step = obs["step"] if isinstance(obs, dict) else obs.step
    player = obs["player"] if isinstance(obs, dict) else obs.player
    rng = random.Random(step * 31 + player)

    market = []
    for _ in range(rng.randint(0, 4)):
        r = rng.random()
        if r < 0.35:
            market.append(["BUY_SEED", rng.choice(CROPS), rng.randint(1, 3)])
        elif r < 0.5:
            market.append(["SELL", rng.choice(["WHEAT", "CARROT", "MELON", "EGG", "FERTILIZER"]), rng.randint(1, 9)])
        elif r < 0.62:
            market.append(["BUY_PRODUCT", rng.choice(["WHEAT", "FERTILIZER"]), rng.randint(1, 5)])
        elif r < 0.72:
            market.append(["BUY_ANIMAL", rng.choice(["GOOSE", "COW", "SHEEP"]), 1])
        elif r < 0.92:
            market.append(["HIRE"])
        else:
            market.append(["BUY_LAND"])

    def unit_op():
        r = rng.random()
        if r < 0.22:
            return ["PLANT", rng.choice(CROPS)]
        if r < 0.3:
            return ["PICKUP", rng.choice(["WHEAT", "FERTILIZER", "GOOSE", "COW", "SHEEP"]), rng.randint(1, 4)]
        if r < 0.38:
            return ["PLACE", rng.choice(["GOOSE", "COW", "SHEEP", "WHEAT"]), rng.randint(1, 2)]
        return [rng.choice(UNIT_OPS)]

    farms = obs["farms"] if isinstance(obs, dict) else obs.farms
    n_hands = len(farms[player]["hands"])
    return {"farmer": unit_op(), "hands": [unit_op() for _ in range(n_hands)], "market": market}


def digest(farms, market, town) -> str:
    return json.dumps({
        "money": [round(f["money"], 6) for f in farms],
        "tiles": [f["tiles"] for f in farms],
        "farmer": [f["farmer"] for f in farms],
        "hands": [f["hands"] for f in farms],
        "quads": [sorted(f["unlocked_quadrants"]) for f in farms],
        "hires": [f["hires_today"] for f in farms],
        "inv": market["inventory"],
        "prices": market["prices"],
        "shops": town["unlocked_shops"],
    }, sort_keys=True, default=str)


def official(seed: int, steps: int, pair):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed}, debug=True)
    env.run(list(pair))
    last = env.steps[-1]
    o = last[0].observation
    return {
        "rewards": [float(s.reward) for s in last],
        "digest": digest(o["farms"], o["market"], o["town"]),
        "n_steps": len(env.steps),
    }


def fast(seed: int, steps: int, pair):
    g = fastsim.Game(seed, {"episodeSteps": steps})
    for _ in range(steps - 1):
        g.step([pair[0](g.obs(0)), pair[1](g.obs(1))])
        if g.done:
            break
    o = g.state[0].observation
    return {
        "rewards": g.rewards(),
        "digest": digest(o.farms, o.market, o.town),
        "n_steps": g.step_n + 1,
    }


def main(n_seeds: int = 3, steps: int = 720) -> int:
    bad = 0
    starter = fastsim.REF.starter_agent
    pairs = {"noisy/noisy": (noisy_agent, noisy_agent),
             "starter/noisy": (starter, noisy_agent),
             "starter/starter": (starter, starter)}
    for seed in range(1, n_seeds + 1):
      for label, pair in pairs.items():
        a, b = official(seed, steps, pair), fast(seed, steps, pair)
        ok = a["rewards"] == b["rewards"] and a["digest"] == b["digest"] and a["n_steps"] == b["n_steps"]
        print(f"seed {seed} {label:16s}: {'MATCH' if ok else 'MISMATCH'}  official={a['rewards']} fast={b['rewards']}"
              f"  steps {a['n_steps']}/{b['n_steps']}")
        if not ok:
            bad += 1
            if a["digest"] != b["digest"]:
                da, db = json.loads(a["digest"]), json.loads(b["digest"])
                for k in da:
                    if da[k] != db[k]:
                        print(f"  first differing field: {k}")
                        print(f"    official: {str(da[k])[:300]}")
                        print(f"    fast    : {str(db[k])[:300]}")
                        break
    print("PARITY OK" if not bad else f"PARITY FAILED on {bad}/{n_seeds} seeds")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(*(int(a) for a in sys.argv[1:])))
