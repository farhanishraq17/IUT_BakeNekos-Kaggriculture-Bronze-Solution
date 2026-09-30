"""Where do the last coins go? End-of-season audit for near-mirror matches.

Twins decide games by single-digit coins, so any spend that cannot pay back
before step 719, or any stock left unsold at the end, is a flippable game.
Per player, over the last day: money spent by market order type and on hires;
at the final state: shed + carried stock and its value at final prices.

    python runs/endgame_probe.py A B seed n
"""
import collections
import sys
from multiprocessing import Pool

sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents  # noqa: E402

LAST = 24   # steps audited at the end


def one(job):
    a, b, seed, seat = job
    A, B = opponents.get(a), opponents.get(b)
    agents = (A, B) if seat == 0 else (B, A)
    g = fastsim.Game(seed)
    cfg = g.env.configuration
    two = [fastsim._takes_config(f) for f in agents]
    steps = cfg["episodeSteps"]
    spend = [collections.Counter(), collections.Counter()]
    for t in range(steps - 1):
        acts = []
        for i, fn in enumerate(agents):
            o = g.obs(i)
            try:
                acts.append(fn(o, cfg) if two[i] else fn(o))
            except Exception:
                acts.append(fastsim.PASS)
        before = list(g.money)
        g.step(acts)
        if t >= steps - 1 - LAST:
            for i in (0, 1):
                ops = collections.Counter(o[0] for o in (acts[i].get("market") or []) if isinstance(o, list) and o)
                for u in [acts[i].get("farmer") or []] + list(acts[i].get("hands") or []):
                    if u:
                        ops["unit:" + u[0]] += 1
                delta = g.money[i] - before[i]
                spend[i]["net"] += delta
                for k, v in ops.items():
                    spend[i][k] += v
        if g.done:
            break
    out = []
    prices = g.obs(0)["market"]["prices"]
    for i in (0, 1):
        o = g.obs(i)
        priv = o["private"]
        stock = collections.Counter({k: v for k, v in priv["shed"].items() if v > 0})
        carried = collections.Counter()
        for inv in priv["inventories"]:
            for k, v in inv.items():
                if v > 0:
                    carried[k] += v
        val = sum(v * prices.get(k, 0) for k, v in stock.items() if k in prices)
        cval = sum(v * prices.get(k, 0) for k, v in carried.items() if k in prices)
        out.append(dict(money=g.money[i], shed=dict(stock), shed_val=val, carried=dict(carried),
                        carried_val=cval, last=dict(spend[i])))
    me, them = (out[0], out[1]) if seat == 0 else (out[1], out[0])
    return a, b, seed, seat, me, them


if __name__ == "__main__":
    a, b, s0, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    jobs = [(a, b, s, seat) for s in range(s0, s0 + n) for seat in (0, 1)]
    with Pool(min(len(jobs), 12)) as p:
        for a_, b_, seed, seat, me, them in p.imap(one, jobs):
            print(f"seed {seed} seat {seat}: {a_} ${me['money']:,.0f} vs ${them['money']:,.0f} "
                  f"(diff {me['money']-them['money']:+,.0f})")
            for tag, r in (("me", me), ("them", them)):
                print(f"   {tag:4s} shed={r['shed']} (${r['shed_val']:,.0f})  carried={r['carried']} "
                      f"(${r['carried_val']:,.0f})  last{LAST}={r['last']}")
