"""External shed-overflow guard: wraps ANY agent (no internals access needed) and
proactively sells excess stock before the end-of-day shedCapacity cap discards it.

This generalizes the round-1 finding (tetsutani's internal `_SR_MARGIN`/`_Y_MARGIN`
guards were miscalibrated -- too conservative, so they fired too late) into a
standalone layer we can apply to agents whose internals we cannot safely edit
(koshinm: 6 nested compression layers, no accessible named constants -- see
CLAUDE.md "koshinm's internals").

Mechanism: after the base agent's action, project end-of-day shed + carried
inventory. If it exceeds shedCapacity - margin, append SELL orders (highest
price first) for the excess, skipping items the base action is already selling
and respecting maxMarketOrdersPerTurn.
"""
from __future__ import annotations

PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def _get(obs, key, default=None):
    return obs[key] if isinstance(obs, dict) else getattr(obs, key, default)


def wrap(base_agent, margin: int = 10, min_price: int = 2, hour_min: int = 0, wheat_keep: int = 0,
         skip=(), seed_cutoff: int = 10**9, fert_cutoff: int = 10**9):
    """margin: how far below shedCapacity to start proactively selling (higher =
    more proactive, matches the round-1 _SR_MARGIN/_Y_MARGIN convention where a
    LARGER margin triggers the guard EARLIER)."""
    import inspect
    try:
        takes_config = len(inspect.signature(base_agent).parameters) >= 2
    except (TypeError, ValueError):
        takes_config = False

    def agent(observation, configuration=None):
        action = base_agent(observation, configuration) if takes_config else base_agent(observation)
        try:
            action = _late_filter(observation, action, seed_cutoff, fert_cutoff)
            if int(_get(observation, "hour", 0) or 0) < hour_min:
                return action
            return _guard(observation, action, margin, min_price, wheat_keep, skip)
        except Exception:
            return action

    return agent


def _late_filter(obs, action, seed_cutoff, fert_cutoff):
    """Drop purchases that cannot pay back before the season ends: seeds after
    seed_cutoff (every crop needs >= 2 days to a first harvest; these end up
    stranded unplanted), fertilizer after fert_cutoff (no growing left)."""
    step = int(_get(obs, "step", 0) or 0)
    if step < min(seed_cutoff, fert_cutoff) or not isinstance(action, dict):
        return action
    kept = []
    for o in action.get("market") or []:
        if isinstance(o, list) and o:
            if o[0] == "BUY_SEED" and step >= seed_cutoff:
                continue
            if o[0] == "BUY_PRODUCT" and len(o) > 1 and o[1] == "FERTILIZER" and step >= fert_cutoff:
                continue
        kept.append(o)
    return dict(action, market=kept)


def _guard(obs, action, margin, min_price, wheat_keep=0, skip=()):
    if not isinstance(action, dict):
        return action
    player = _get(obs, "player")
    farms = _get(obs, "farms")
    private = _get(obs, "private")
    market = _get(obs, "market")
    if player is None or not farms or not private or not market:
        return action
    farm = farms[player]
    shed = dict(private.get("shed", {}) if isinstance(private, dict) else private["shed"])
    orders = list(action.get("market") or [])
    if len(orders) >= 10:
        return action

    # Project what this turn's action already does to the shed/carried total.
    already_selling = {o[1] for o in orders if isinstance(o, list) and len(o) >= 2 and o[0] == "SELL"}
    inventories = private.get("inventories", []) if isinstance(private, dict) else private["inventories"]
    carried = sum(max(0, int(v)) for inv in inventories for v in inv.values())
    units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
    for i, cmd in enumerate(units):
        if not cmd:
            continue
        op = cmd[0]
        if op == "HARVEST":
            pos = farm["farmer"] if i == 0 else (farm["hands"][i - 1] if i - 1 < len(farm["hands"]) else None)
            if pos:
                tile = farm["tiles"][pos[1]][pos[0]]
                if isinstance(tile, dict):
                    carried += max(0, int(tile.get("yield_units", 0)))
        elif op == "COLLECT_FERTILIZER":
            carried += 1
        elif op == "DROP":
            carried = max(0, carried - sum(max(0, int(v)) for v in (inventories[i] if i < len(inventories) else {}).values()))

    total = sum(max(0, int(v)) for v in shed.values()) + carried
    cap = int((configuration := action.get("_cfg", None)) or 100)
    # configuration isn't passed through action; use default 100 (shedCapacity default).
    cap = 100
    excess = total - cap + margin
    if excess <= 0:
        return action

    prices = market.get("prices", {})
    cands = sorted(
        ((int(prices.get(it, 0)), it, int(shed.get(it, 0))) for it in PRODUCTS
         if it not in already_selling and it not in skip and int(shed.get(it, 0)) > 0
         and int(prices.get(it, 0)) >= min_price),
        reverse=True,
    )
    extra = []
    need = excess
    for price, item, avail in cands:
        if need <= 0 or len(orders) + len(extra) >= 10:
            break
        if item == "WHEAT":
            avail = max(0, avail - wheat_keep)
        qty = min(need, avail)
        if qty > 0:
            extra.append(["SELL", item, qty])
            need -= qty
    if not extra:
        return action
    return dict(action, market=orders + extra)
