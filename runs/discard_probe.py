"""How much stock still gets discarded at the 100-item shed cap, per agent?

Monkeypatches the pinned engine's _drop_inventories_to_shed to count overflow
(units and their market value) per player, then plays a candidate against a panel.
Tells us how much value the guard is still leaving on the table.
"""
import sys, collections
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents

REF = fastsim.REF
_orig = REF._drop_inventories_to_shed
LOST = collections.Counter()      # (player, item) -> units discarded
_ctx = {"calls": 0}   # engine calls this once per player per day, pid 0 then 1


def _counting_drop(private, capacity):
    pid = _ctx["calls"] % 2
    _ctx["calls"] += 1
    shed = private["shed"]
    before = sum(shed.values())
    incoming = collections.Counter()
    for inv in private["inventories"]:
        for item, n in inv.items():
            if n > 0:
                incoming[item] += n
    _orig(private, capacity)
    after = sum(shed.values())
    kept = after - before
    total_in = sum(incoming.values())
    over = total_in - kept
    if over > 0:
        # attribute the overflow to the cheapest-last order the engine used
        for item, n in incoming.most_common():
            take = min(n, over)
            LOST[(pid, item)] += take
            over -= take
            if over <= 0:
                break


REF._drop_inventories_to_shed = _counting_drop


def probe(cand, opps, seeds):
    rows = []
    for name in opps:
        opp = opponents.get(name)
        for seed in seeds:
            LOST.clear(); _ctx["calls"] = 0
            m = fastsim.run(opponents.get(cand), opp, seed=seed)
            rows.append((name, seed, m, sum(LOST.values()), dict(LOST)))
    return rows


if __name__ == "__main__":
    cand = sys.argv[1]
    opps = sys.argv[2].split(",")
    seeds = range(int(sys.argv[3]), int(sys.argv[3]) + int(sys.argv[4]))
    mine, theirs = collections.Counter(), collections.Counter()
    games = 0
    for name, seed, m, lost, detail in probe(cand, opps, seeds):
        games += 1
        for (pid, item), v in detail.items():
            (mine if pid == 0 else theirs)[item] += v
    print(f"{cand}: {games} games")
    print(f"  us      {sum(mine.values()):6d} units ({sum(mine.values())/games:5.1f}/game)  {dict(mine)}")
    print(f"  opponent{sum(theirs.values()):6d} units ({sum(theirs.values())/games:5.1f}/game)  {dict(theirs)}")
