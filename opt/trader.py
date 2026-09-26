"""External wheat-speculation wrapper.

Same shape as shed_guard.py: run the base agent's action unchanged, then spend
spare market-order slots on a trade the base never makes.

Why wheat: `_parse_order` only allows BUY_PRODUCT for WHEAT and FERTILIZER, and
of those two only wheat appreciates. Wheat sits on a log glut curve (6000 units
dumped still leaves it at $19) while the town drains it every 4 steps, so the
price climbs through the season -- CLAUDE.md measures $25 -> $46. Fertilizer is
excluded from all town demand, so its inventory only ever grows and its price
only ever falls: never buy it.

The trade: buy wheat early while it is cheap, hold, sell it back late at the
higher price. Constraints that make this small and safe:

- The 100-item shed cap counts wheat, so a big position would be discarded at
  end of day (or dumped by shed_guard). `max_hold` keeps the position tiny.
- The base agent feeds its herd from shed wheat, and selling feed out from under
  it loses animals permanently (CLAUDE.md bug #2). We only ever sell wheat WE
  bought, tracked in `bought`, and never below `feed_floor`.
- Buying moves the price against ourselves, one unit at a time, so purchases are
  capped per turn.
"""

from __future__ import annotations

_STATE: dict[int, dict] = {}


def wrap(base_agent, buy_below: int = 28, buy_until: int = 240, sell_after: int = 500,
         max_hold: int = 20, per_turn: int = 5, cash_reserve: int = 3000,
         feed_floor: int = 10, sell_above: int = 34):
    """Return base_agent with the wheat-trading layer appended.

    buy_below     only buy at or under this price
    buy_until     stop accumulating after this step
    sell_after    start unwinding at this step
    max_hold      never hold more than this many bought units (shed cap is 100)
    cash_reserve  never spend the base's operating cash below this
    feed_floor    never let shed wheat drop below this when unwinding
    sell_above    only unwind at or above this price
    """
    import inspect
    try:
        two = len(inspect.signature(base_agent).parameters) >= 2
    except (TypeError, ValueError):
        two = False

    def agent(observation, configuration=None):
        action = base_agent(observation, configuration) if two else base_agent(observation)
        try:
            return _trade(observation, action, buy_below, buy_until, sell_after,
                          max_hold, per_turn, cash_reserve, feed_floor, sell_above)
        except Exception:
            return action

    return agent


def _trade(obs, action, buy_below, buy_until, sell_after, max_hold, per_turn,
           cash_reserve, feed_floor, sell_above):
    if not isinstance(action, dict):
        return action
    step = int(obs.get("step") or 0)
    pid = int(obs.get("player") or 0)
    st = _STATE.get(pid)
    if st is None or step <= 0:
        st = _STATE[pid] = {"bought": 0}

    orders = list(action.get("market") or [])
    if len(orders) >= 10:
        return action
    # never fight the base for the same item in the same turn
    if any(isinstance(o, list) and len(o) > 1 and o[1] == "WHEAT" for o in orders):
        return action

    market = obs.get("market") or {}
    price = int((market.get("prices") or {}).get("WHEAT", 0))
    if price <= 0:
        return action

    farms = obs.get("farms") or []
    money = 0
    if pid < len(farms):
        try:
            money = int(farms[pid].get("money", 0))
        except (TypeError, ValueError):
            money = 0
    shed = (obs.get("private") or {}).get("shed") or {}
    held = int(shed.get("WHEAT", 0))

    if step <= buy_until and price <= buy_below and st["bought"] < max_hold:
        room = max_hold - st["bought"]
        # shed cap: leave headroom so the position is never what gets discarded
        cap_room = max(0, 100 - sum(max(0, int(v)) for v in shed.values()) - 20)
        afford = max(0, (money - cash_reserve)) // price
        qty = min(per_turn, room, cap_room, afford)
        if qty > 0:
            st["bought"] += qty
            return dict(action, market=orders + [["BUY_PRODUCT", "WHEAT", int(qty)]])

    if step >= sell_after and st["bought"] > 0 and price >= sell_above:
        qty = min(st["bought"], max(0, held - feed_floor))
        if qty > 0:
            st["bought"] -= qty
            return dict(action, market=orders + [["SELL", "WHEAT", int(qty)]])

    return action


def demo():
    """Self-check: buys cheap early, unwinds dear late, never touches the base's
    feed, never exceeds the order cap, and never sells more than it bought."""
    def obs_at(step, price, shed_wheat, money=50000, orders=None):
        return {"step": step, "player": 0,
                "market": {"prices": {"WHEAT": price}, "inventory": {"WHEAT": 9000}},
                "private": {"shed": {"WHEAT": shed_wheat}},
                "farms": [{"money": money}, {"money": money}]}, \
               {"farmer": ["PASS"], "hands": [], "market": list(orders or [])}

    _STATE.clear()
    o, a = obs_at(10, 25, 5)
    out = _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)
    assert out["market"] == [["BUY_PRODUCT", "WHEAT", 5]], out["market"]
    assert _STATE[0]["bought"] == 5

    # too expensive to buy
    o, a = obs_at(20, 40, 5)
    assert _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)["market"] == []

    # past the accumulation window
    o, a = obs_at(300, 25, 5)
    assert _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)["market"] == []

    # unwind late, but only down to the feed floor: shed 14, floor 10 -> sell 4
    o, a = obs_at(600, 46, 14)
    out = _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)
    assert out["market"] == [["SELL", "WHEAT", 4]], out["market"]
    assert _STATE[0]["bought"] == 1, _STATE

    # never sells below the feed floor
    o, a = obs_at(601, 46, 9)
    assert _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)["market"] == []

    # defers to the base when it is already trading wheat this turn
    o, a = obs_at(11, 25, 5, orders=[["SELL", "WHEAT", 3]])
    assert _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)["market"] == [["SELL", "WHEAT", 3]]

    # respects the 10-order cap
    o, a = obs_at(12, 25, 5, orders=[["SELL", "EGG", 1]] * 10)
    assert len(_trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)["market"]) == 10

    # keeps the operating cash reserve intact
    _STATE.clear()
    o, a = obs_at(10, 25, 5, money=3050)
    assert _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)["market"] == [["BUY_PRODUCT", "WHEAT", 2]]

    # state resets at step 0 (fastsim reuses the process across games)
    o, a = obs_at(0, 25, 5)
    _trade(o, a, 28, 240, 500, 20, 5, 3000, 10, 34)
    assert _STATE[0]["bought"] <= 5
    print("trader self-check OK")


if __name__ == "__main__":
    demo()
