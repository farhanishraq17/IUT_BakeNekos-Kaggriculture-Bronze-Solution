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
         cheap_first: bool = False,
         skip=(), seed_cutoff: int = 10**9, fert_cutoff: int = 10**9, endgame_step: int = 10**9,
         late_step: int = 10**9, late_margin: int = 60, topup: bool = False, topup_end: bool = False):
    """margin: how far below shedCapacity to start proactively selling (higher =
    more proactive, matches the round-1 _SR_MARGIN/_Y_MARGIN convention where a
    LARGER margin triggers the guard EARLIER).

    endgame_step: from this step on, sell ALL shed stock every turn (skip list
    ignored -- unsold stock scores zero). Against a twin running the same
    liquidation tape, this sells each unit before the twin dumps the same item.

    late_step: from this step (until endgame_step) the guard runs at late_margin.
    Margins above ~32 collapse mid-season (p30), plausibly by starving working
    stock; near the end there is no season left for that to cost anything."""
    import inspect
    try:
        takes_config = len(inspect.signature(base_agent).parameters) >= 2
    except (TypeError, ValueError):
        takes_config = False

    def agent(observation, configuration=None):
        action = base_agent(observation, configuration) if takes_config else base_agent(observation)
        try:
            action = _late_filter(observation, action, seed_cutoff, fert_cutoff)
            if int(_get(observation, "step", 0) or 0) >= endgame_step:
                return _guard(observation, action, 1000, min_price, 0, (), False, topup or topup_end)
            if int(_get(observation, "step", 0) or 0) >= late_step:
                return _guard(observation, action, late_margin, min_price, wheat_keep, skip, cheap_first, topup)
            if int(_get(observation, "hour", 0) or 0) < hour_min:
                return action
            return _guard(observation, action, margin, min_price, wheat_keep, skip, cheap_first, topup)
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


def _guard(obs, action, margin, min_price, wheat_keep=0, skip=(), cheap_first=False, topup=False):
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
    if topup:
        return _guard_topup(action, orders, shed, prices, excess, min_price, wheat_keep, skip, cheap_first)
    cands = sorted(
        ((int(prices.get(it, 0)), it, int(shed.get(it, 0))) for it in PRODUCTS
         if it not in already_selling and it not in skip and int(shed.get(it, 0)) > 0
         and int(prices.get(it, 0)) >= min_price),
        # Default: dump the most valuable stock first (most cash per unit now).
        # cheap_first inverts it: premium goods (WOOL 59 / MILK 76 / STRAWBERRY 62
        # units to the $1 floor) crash permanently once dumped, while WHEAT and EGG
        # sit on a log glut curve and barely move -- so clearing the cap with bulk
        # may preserve far more value than clearing it with premium.
        reverse=not cheap_first,
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


def _guard_topup(action, orders, shed, prices, excess, min_price, wheat_keep, skip, cheap_first):
    """Option T: like the guard, but an item the base is already selling is not
    skipped -- its existing SELL order is raised instead (the base often sells 2-3
    of a 40-unit stack; the rest would wait for a later turn than the twin's)."""
    sold = {}
    for o in orders:
        if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL":
            try:
                sold[o[1]] = sold.get(o[1], 0) + int(o[2])
            except (TypeError, ValueError):
                return action
    cands = sorted(
        ((int(prices.get(it, 0)), it, int(shed.get(it, 0)) - sold.get(it, 0)) for it in PRODUCTS
         if it not in skip and int(shed.get(it, 0)) - sold.get(it, 0) > 0
         and int(prices.get(it, 0)) >= min_price),
        reverse=not cheap_first,
    )
    extra, bump, need = [], {}, excess
    for price, item, avail in cands:
        if need <= 0:
            break
        if item == "WHEAT":
            avail = max(0, avail - wheat_keep)
        qty = min(need, avail)
        if qty <= 0:
            continue
        if item in sold:
            bump[item] = qty
        elif len(orders) + len(extra) < 10:
            extra.append(["SELL", item, qty])
        else:
            continue
        need -= qty
    if not extra and not bump:
        return action
    out = []
    for o in orders:
        if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL" and o[1] in bump:
            o = ["SELL", o[1], int(o[2]) + bump.pop(o[1])]
        out.append(o)
    return dict(action, market=out + extra)

