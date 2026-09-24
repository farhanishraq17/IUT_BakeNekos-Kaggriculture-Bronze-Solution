"""Why doesn't sale_advance fire? Count the reason at every decision point."""
import sys, collections
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents, sale_advance as sa

R = collections.Counter()
_orig = sa._advance

def traced(obs, action, lead, min_events, min_units, min_price, max_orders, start_step):
    step = int(obs.get("step") or 0)
    out = _orig(obs, action, lead, min_events, min_units, min_price, max_orders, start_step)
    st = sa._STATE.get(int(obs.get("player") or 0)) or {}
    orders = sa._orders(action)
    R["turns"] += 1
    if step < start_step:
        R["too_early"] += 1
    elif len(orders) >= max_orders:
        R["no_free_slots"] += 1
    else:
        due = (step + lead) % 24
        ev = [k for k, n in (st.get("events") or {}).items() if k[1] == due and n >= min_events]
        shed = (obs.get("private") or {}).get("shed") or {}
        if not ev:
            R["no_event_due"] += 1
        elif not any(shed.get(i, 0) > 0 for i, _h in ev):
            R["event_but_empty_shed"] += 1
        else:
            R["FIRED" if out is not action else "blocked_other"] += 1
    R["events_total"] = len(st.get("events") or {})
    R["max_orders_seen"] = max(R["max_orders_seen"], len(orders))
    return out

sa._advance = traced
me = opponents.get("adv:guard:c-frontier-0923:14:1:3")
opp = opponents.get(sys.argv[1] if len(sys.argv) > 1 else "c-koshinm-0921")
m = fastsim.run(me, opp, seed=555001)
print("result", m)
for k, v in R.most_common():
    print(f"  {k:22s} {v}")
