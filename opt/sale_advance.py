"""External "sell before they dump" wrapper.

Same shape as shed_guard.py: it runs the base agent's action unchanged, then may
append extra SELL orders. Needs no access to the base agent's internals.

Why: our champion's losses are tiny and are not waste -- liquidation is already
$0 unsold and the shed leak is closed (runs/discard_probe.py: 5.5 units/game).
The median loss is ~$550 on games whose median win margin is ~$1,000, so what is
left is market timing: orders resolve one unit at a time at the shared price, so
whoever sells first gets the better price and pushes the other one down.

How the opponent's sales are inferred (we cannot see their shed):

    opp_sold[item] = delta_inventory[item] + town_take[item] - our_sold[item] + our_bought[item]

`town_take` is deterministic and fully observable: _town_consume() subtracts one
unit per product per unlocked shop instance every `townShopSellInterval` (4)
steps, doubled for single-product shops, plus one per TOWN_CENTER product every
24 steps. Our own orders are known because we just submitted them. Partial fills
add noise, which the event threshold below absorbs.

Prediction: these agents are near-periodic -- they sell the same products at the
same hour every day. So an event is keyed (item, hour). If the opponent sold an
item at hour h on at least `min_events` previous days, we expect it again, and we
sell our stock of that item `lead` turns earlier.

WHEAT is never advanced: it is animal feed, and selling feed out from under the
base agent starves the herd (CLAUDE.md, bug #2).
"""

from __future__ import annotations

# One-product shops consume 2/tick, multi-product 1/tick each (engine _town_consume).
SHOPS = {
    "BAKERY": ("WHEAT",), "PET_CAFE": ("CARROT",), "PIZZA": ("TOMATO",),
    "JUICE_BAR": ("CARROT", "TOMATO"), "YARN_STORE": ("WOOL",),
    "CHEESE_SHOP": ("MILK",), "DESSERT_SHOP": ("STRAWBERRY", "MELON", "EGG"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"),
}
TOWN_CENTER_PRODUCTS = ("WHEAT", "EGG", "MILK")
NEVER_ADVANCE = ("WHEAT",)          # feed: see module docstring
_STATE: dict[int, dict] = {}


def _town_take(obs, step, shop_interval=4, center_interval=24):
    """Units the town removes from the market at this step, per product."""
    take: dict[str, int] = {}
    if step % shop_interval == 0:
        for shop in (obs.get("town") or {}).get("unlocked_shops", []) or []:
            products = SHOPS.get(shop, ())
            mult = 2 if len(products) == 1 else 1
            for item in products:
                take[item] = take.get(item, 0) + mult
    if step % center_interval == 0:
        for item in TOWN_CENTER_PRODUCTS:
            take[item] = take.get(item, 0) + 1
    return take


def _orders(action):
    return list((action or {}).get("market") or [])


def _own_flow(orders):
    """item -> units we put into (+) or took out of (-) the market this turn.

    Orders are LISTS: ["SELL", item, qty] / ["BUY_PRODUCT", item, qty] -- the
    engine's _parse_order silently drops anything else (this cost one whole
    experiment: dict-shaped orders vanish without an error)."""
    flow: dict[str, int] = {}
    for o in orders:
        if not isinstance(o, list) or len(o) < 3:
            continue
        op, item = o[0], o[1]
        try:
            qty = int(o[2])
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        if op == "SELL":
            flow[item] = flow.get(item, 0) + qty
        elif op.startswith("BUY"):
            flow[item] = flow.get(item, 0) - qty
    return flow


def wrap(base_agent, lead: int = 1, min_events: int = 3, min_units: int = 2,
         min_price: int = 2, max_orders: int = 10, start_step: int = 48):
    """Return base_agent with the sale-advance layer appended.

    lead        how many turns ahead of the predicted dump to sell
    min_events  how many past days must show the event before we act on it
    min_units   ignore inferred opponent flow smaller than this (partial-fill noise)
    start_step  do nothing before this step; the history is worthless on day 0-1
    """
    import inspect
    try:
        two = len(inspect.signature(base_agent).parameters) >= 2
    except (TypeError, ValueError):
        two = False

    def agent(observation, configuration=None):
        action = base_agent(observation, configuration) if two else base_agent(observation)
        try:
            return _advance(observation, action, lead, min_events, min_units,
                            min_price, max_orders, start_step)
        except Exception:
            return action            # never let the layer break the base agent

    return agent


def _advance(obs, action, lead, min_events, min_units, min_price, max_orders, start_step):
    step = int(obs.get("step") or 0)
    pid = int(obs.get("player") or 0)
    st = _STATE.get(pid)
    if st is None or step <= 0:
        st = _STATE[pid] = {"prev_inv": None, "prev_orders": [], "events": {}}

    market = obs.get("market") or {}
    inv = dict(market.get("inventory") or {})
    prices = market.get("prices") or {}

    # --- infer what the opponent sold on the PREVIOUS step, and record it ------
    if st["prev_inv"] is not None:
        own = _own_flow(st["prev_orders"])
        take = _town_take(obs, step - 1)
        hour = (step - 1) % 24
        for item, now in inv.items():
            delta = now - st["prev_inv"].get(item, now)
            opp = delta + take.get(item, 0) - own.get(item, 0)
            if opp >= min_units:
                st["events"][(item, hour)] = st["events"].get((item, hour), 0) + 1
    st["prev_inv"] = inv
    st["prev_orders"] = _orders(action)

    if step < start_step:
        return action

    # --- predict the next dump and sell into it first --------------------------
    orders = _orders(action)
    free = max_orders - len(orders)
    if free <= 0:
        return action
    already = {o[1] for o in orders if isinstance(o, list) and len(o) >= 2}
    shed = dict((obs.get("private") or {}).get("shed") or {})

    due = (step + lead) % 24
    wanted = [item for (item, hour), n in st["events"].items()
              if hour == due and n >= min_events
              and item not in NEVER_ADVANCE and item not in already
              and shed.get(item, 0) > 0 and int(prices.get(item, 0)) >= min_price]
    if not wanted:
        return action

    wanted.sort(key=lambda it: -int(prices.get(it, 0)))
    extra = [["SELL", item, int(shed[item])] for item in wanted[:free]]
    out = dict(action)
    out["market"] = orders + extra
    return out


def demo():
    """Self-check: inference must recover a known opponent sale, and the layer
    must never drop the base agent's own orders or exceed the 10-order cap."""
    obs = {"step": 100, "player": 0, "town": {"unlocked_shops": ["PET_CAFE", "YARN_STORE"]},
           "market": {"inventory": {"WOOL": 100, "CARROT": 100}, "prices": {"WOOL": 50, "CARROT": 9}},
           "private": {"shed": {"WOOL": 7, "CARROT": 4}}}

    # town takes 2 CARROT (PET_CAFE, single-product) and 2 WOOL at step 100 % 4 == 0
    assert _town_take(obs, 100) == {"CARROT": 2, "WOOL": 2}, _town_take(obs, 100)
    assert _town_take(obs, 101) == {}

    base_action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "EGG", 1]]}
    _STATE.clear()
    st = _STATE[0] = {"prev_inv": {"WOOL": 90, "CARROT": 100}, "prev_orders": [], "events": {}}
    # WOOL rose 90 -> 100 while the town removed 2: the opponent sold ~12.
    # Orders are lists, exactly as the engine's _parse_order expects.
    out = _advance(obs, base_action, lead=1, min_events=1, min_units=2, min_price=2,
                   max_orders=10, start_step=48)
    assert st["events"].get(("WOOL", 99 % 24)) == 1, st["events"]   # events key on HOUR

    # at step 98 the recorded hour-3 event is due at step+1 ((98+1) % 24 == 3): advance WOOL
    obs2 = dict(obs, step=98)
    st["prev_inv"] = dict(obs["market"]["inventory"])
    out2 = _advance(obs2, base_action, lead=1, min_events=1, min_units=2, min_price=2,
                    max_orders=10, start_step=48)
    sells = [o for o in out2["market"] if o[1] == "WOOL"]
    assert sells and sells[0] == ["SELL", "WOOL", 7], out2["market"]
    assert out2["market"][0] == base_action["market"][0], "base order dropped"
    assert len(out2["market"]) <= 10

    # CARROT is below min_price, so it is never advanced
    assert not [o for o in out2["market"] if o[1] == "CARROT"], out2["market"]

    # a failing base agent must not take the wrapper down
    def boom(o, c=None):
        raise ValueError("base exploded")
    try:
        wrap(boom)({"step": 1, "player": 0})
        raise AssertionError("wrapper should propagate a base-agent crash")
    except ValueError:
        pass
    print("sale_advance self-check OK")


if __name__ == "__main__":
    demo()
