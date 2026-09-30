"""Why does stock still get discarded under the guard? Per discard event: day,
player, units lost by item, shed before the drop, and what the player's market
orders were on the last few turns of that day.

    python runs/leak_trace.py CAND OPP seed n
"""
import collections
import sys

sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents  # noqa: E402

REF = fastsim.REF
_orig = REF._drop_inventories_to_shed
EVENTS = []
CTX = {"calls": 0, "step": 0}


def _drop(private, capacity):
    pid = CTX["calls"] % 2
    CTX["calls"] += 1
    shed_before = dict((k, v) for k, v in private["shed"].items() if v > 0)
    incoming = collections.Counter()
    for inv in private["inventories"]:
        for k, n in inv.items():
            if n > 0:
                incoming[k] += n
    before = sum(private["shed"].values())
    _orig(private, capacity)
    over = sum(incoming.values()) - (sum(private["shed"].values()) - before)
    if over > 0:
        EVENTS.append(dict(step=CTX["step"], pid=pid, lost=over, incoming=dict(incoming),
                           shed=shed_before, shed_total=before))


REF._drop_inventories_to_shed = _drop


def play(a, b, seed):
    A, B = opponents.get(a), opponents.get(b)
    g = fastsim.Game(seed)
    cfg = g.env.configuration
    hist = collections.deque(maxlen=4)
    EVENTS.clear(); CTX["calls"] = 0
    for t in range(cfg["episodeSteps"] - 1):
        CTX["step"] = t
        acts = [A(g.obs(0), cfg), B(g.obs(1), cfg)]
        hist.append((t, [x.get("market") for x in acts]))
        n0 = len(EVENTS)
        g.step(acts)
        for e in EVENTS[n0:]:
            e["recent_market"] = [(s, m[e["pid"]]) for s, m in hist]
        if g.done:
            break
    return g.money, list(EVENTS)


if __name__ == "__main__":
    a, b, s0, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    for seed in range(s0, s0 + n):
        money, ev = play(a, b, seed)
        print(f"seed {seed}: {money}  events={len(ev)}")
        for e in ev:
            who = "CAND" if e["pid"] == 0 else "opp "
            print(f"  {who} step {e['step']} (day {e['step']//24}) lost {e['lost']} shed_total={e['shed_total']} "
                  f"incoming={e['incoming']}")
            print(f"       shed={e['shed']}")
            for s, m in e["recent_market"]:
                print(f"       t{s}: {m}")
