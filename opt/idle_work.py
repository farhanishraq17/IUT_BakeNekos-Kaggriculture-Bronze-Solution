"""External "put idle units to work" wrapper.

Same shape as shed_guard.py: runs the base agent's action unchanged, then
replaces PASS (or missing) unit ops with a useful op **on the tile that unit is
already standing on**. No movement, so it can never disturb the base agent's
plan -- a unit that was going to do nothing does something instead, in place.

Why: runs/idle_probe.py on the shipped champion (guard:c-frontier-0923:14)
measures 0.65 PASS ops/turn out of 8.8 hands plus a farmer idling 9.9% of turns
= ~470 wasted unit-actions per game. runs/waste_probe.py on the same games shows
7 fed animals/game never get CARE, each one a forgone +1 production unit.

Engine rules this relies on (kaggriculture_ref.py `_apply_unit_action`): ops act
on the actor's own tile; CARE sets cared_today (a +1 bonus on the next fed
production day) and no-ops if already cared; COLLECT_FERTILIZER takes the tile's
one daily fertilizer and no-ops if unavailable; WATER no-ops on a non-plant.
Every op is a silent no-op when illegal, so a wrong guess costs nothing.

Defaults are CARE-only. Fertilizer is opt-in (`fert=True`): each unit collected
is one more item competing for the 100-slot shed, and the town never buys
FERTILIZER, so its price only falls -- stack it on shed_guard if you enable it.
"""

from __future__ import annotations

_PASSIVE = ("PASS", None, "")


def _tile_at(farm, pos):
    try:
        x, y = int(pos[0]), int(pos[1])
        return farm["tiles"][y][x]
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def _useful_op(tile, care=True, fert=False, water=False):
    """The best legal in-place op for a unit standing on `tile`, or None."""
    if not isinstance(tile, dict):
        return None
    if "animal" in tile:
        # fertilizer first: it is a product in hand now, CARE only pays later
        if fert and tile.get("fertilizer_available"):
            return ["COLLECT_FERTILIZER"]
        if care and not tile.get("cared_today") and tile.get("fed_today"):
            return ["CARE"]
        return None
    if water and tile.get("kind") == "PLANT" and not tile.get("watered_today"):
        return ["WATER"]
    return None


def wrap(base_agent, care: bool = True, fert: bool = False, water: bool = False):
    import inspect
    try:
        two = len(inspect.signature(base_agent).parameters) >= 2
    except (TypeError, ValueError):
        two = False

    def agent(observation, configuration=None):
        action = base_agent(observation, configuration) if two else base_agent(observation)
        try:
            return _fill_idle(observation, action, care, fert, water)
        except Exception:
            return action

    return agent


def _fill_idle(obs, action, care, fert, water):
    if not isinstance(action, dict):
        return action
    farms = obs.get("farms") or []
    pid = int(obs.get("player") or 0)
    if pid >= len(farms):
        return action
    farm = farms[pid]
    hands = list(farm.get("hands") or [])

    out = None
    ops = list(action.get("hands") or [])
    # a unit with no op at all is idle too, so pad out to the real unit count
    ops += [None] * max(0, len(hands) - len(ops))
    for i, op in enumerate(ops):
        if op and op[0] not in _PASSIVE:
            continue
        new = _useful_op(_tile_at(farm, hands[i]), care, fert, water) if i < len(hands) else None
        if new:
            if out is None:
                out = dict(action)
                ops = list(ops)
            ops[i] = new
    if out is not None:
        out["hands"] = ops

    farmer = action.get("farmer") or []
    if not farmer or farmer[0] in _PASSIVE:
        new = _useful_op(_tile_at(farm, farm.get("farmer")), care, fert, water)
        if new:
            out = dict(action) if out is None else out
            out["farmer"] = new
    return out if out is not None else action


def demo():
    """Self-check: fills idle units in place, never touches busy ones, and
    respects the engine's legality rules."""
    animal_cared = {"animal": "COW", "fed_today": True, "cared_today": True, "fertilizer_available": False}
    animal_todo = {"animal": "SHEEP", "fed_today": True, "cared_today": False, "fertilizer_available": True}
    plant_dry = {"kind": "PLANT", "watered_today": False}
    tiles = [[animal_todo, animal_cared], [plant_dry, {"kind": "EMPTY"}]]
    farm = {"tiles": tiles, "farmer": [1, 1], "hands": [[0, 0], [1, 0], [0, 1]]}
    obs = {"player": 0, "farms": [farm]}

    act = {"farmer": ["PASS"], "hands": [["PASS"], ["HARVEST"], None], "market": [["SELL", "EGG", 1]]}
    out = _fill_idle(obs, act, care=True, fert=False, water=False)
    assert out["hands"][0] == ["CARE"], out["hands"]          # idle, animal needs care
    assert out["hands"][1] == ["HARVEST"], out["hands"]       # busy: untouched
    assert out["hands"][2] is None, out["hands"]              # plant, water disabled
    assert out["farmer"] == ["PASS"], out["farmer"]           # EMPTY tile: nothing to do
    assert out["market"] == act["market"], "market orders must pass through"
    assert act["hands"][0] == ["PASS"], "must not mutate the base agent's action"

    # fertilizer takes priority over care when enabled
    out = _fill_idle(obs, act, care=True, fert=True, water=False)
    assert out["hands"][0] == ["COLLECT_FERTILIZER"], out["hands"]

    # water only fires with water=True, and only on an unwatered plant
    out = _fill_idle(obs, act, care=True, fert=False, water=True)
    assert out["hands"][2] == ["WATER"], out["hands"]

    # an unfed animal gets no CARE (the engine only banks the bonus when fed)
    animal_todo["fed_today"] = False
    out = _fill_idle(obs, act, care=True, fert=False, water=False)
    assert out["hands"][0] == ["PASS"], out["hands"]

    # a broken observation must fall back to the base action untouched
    assert wrap(lambda o, c=None: act)({"player": 0}) == act
    print("idle_work self-check OK")


if __name__ == "__main__":
    demo()
