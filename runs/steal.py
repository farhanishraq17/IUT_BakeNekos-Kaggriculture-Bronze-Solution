"""What do our live opponents do that the public base does NOT?

For each live replay: seat the public base agent in the opponent's chair, feed
our own recorded actions back, and walk forward until the base's action differs
from what the opponent actually played. That first divergence is the opponent's
private layer showing itself. Aggregate the divergences over all games.
"""
import json, glob, sys, collections
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents

PASS = {"farmer": ["PASS"], "hands": [], "market": []}

def canon(a):
    return json.dumps(a if isinstance(a, dict) else PASS, sort_keys=True, default=str)

def recorded(rep, p, t):
    st = rep["steps"]
    a = st[t + 1][p].get("action") if t + 1 < len(st) else None
    return a if isinstance(a, dict) else PASS

def diffs(rep, base, opp_seat, limit=719, want=6):
    me = opponents.get(base)
    two = fastsim._takes_config(me)
    g = fastsim.Game(rep["info"]["seed"], {"episodeSteps": rep["configuration"]["episodeSteps"]})
    cfg = g.env.configuration
    out = []
    for t in range(min(limit, len(rep["steps"]) - 1)):
        real = recorded(rep, opp_seat, t)
        try:
            mine = me(g.obs(opp_seat), cfg) if two else me(g.obs(opp_seat))
        except Exception:
            break
        if canon(mine) != canon(real) and len(out) < want:
            out.append((t, mine, real))
        acts = [None, None]
        acts[opp_seat] = real          # follow THEIR actions, so we stay on their trajectory
        acts[1 - opp_seat] = recorded(rep, 1 - opp_seat, t)
        g.step(acts)
        if g.done:
            break
    return out

if __name__ == "__main__":
    base = sys.argv[1]
    market_ops = collections.Counter()
    unit_ops = collections.Counter()
    first_steps = []
    games = 0
    for f in sorted(glob.glob("runs/livediag/*/*.json")):
        rep = json.load(open(f, encoding="utf-8"))
        names = rep["info"]["TeamNames"]
        us = next((i for i, t in enumerate(names) if t == "Farhan Ishraq"), None)
        if us is None:
            continue
        last = rep["steps"][-1]
        rw = [float(s.get("reward") or 0) for s in last]
        if rw[us] >= rw[1 - us]:
            continue                    # only study games we LOST
        games += 1
        d = diffs(rep, base, 1 - us)
        if d:
            first_steps.append(d[0][0])
        for t, mine, real in d:
            for o in (real.get("market") or []):
                if isinstance(o, list) and o:
                    market_ops[(o[0], o[1] if len(o) > 1 else "")] += 1
            for o in (real.get("hands") or []) + [real.get("farmer") or []]:
                if isinstance(o, list) and o:
                    unit_ops[o[0]] += 1
    first_steps.sort()
    print(f"lost games analysed: {games}")
    if first_steps:
        print(f"first divergence from {base}: min {first_steps[0]}, median {first_steps[len(first_steps)//2]}, max {first_steps[-1]}")
    print("\nmarket orders they issue at divergence points:")
    for k, v in market_ops.most_common(12):
        print(f"   {k[0]:14s} {k[1]:12s} {v}")
    print("\nunit ops at divergence points:")
    for k, v in unit_ops.most_common(10):
        print(f"   {k:20s} {v}")
