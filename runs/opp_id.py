"""Which public agent are our LIVE opponents actually running?

For each downloaded live replay, seat a candidate in the opponent's chair, feed
our own recorded actions back, and count how many turns the candidate's action
matches what the opponent really played. A long prefix = that team runs that agent.
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

def match(rep, cand, opp_seat, limit=400):
    me = opponents.get(cand)
    two = fastsim._takes_config(me)
    g = fastsim.Game(rep["info"]["seed"], {"episodeSteps": rep["configuration"]["episodeSteps"]})
    cfg = g.env.configuration
    for t in range(min(limit, len(rep["steps"]) - 1)):
        try:
            mine = me(g.obs(opp_seat), cfg) if two else me(g.obs(opp_seat))
        except Exception:
            return t
        if canon(mine) != canon(recorded(rep, opp_seat, t)):
            return t
        acts = [None, None]
        acts[opp_seat] = mine
        acts[1 - opp_seat] = recorded(rep, 1 - opp_seat, t)
        g.step(acts)
        if g.done:
            break
    return limit

if __name__ == "__main__":
    cands = sys.argv[1].split(",")
    best = collections.Counter()
    rows = []
    for f in sorted(glob.glob("runs/livediag/*/*.json")):
        rep = json.load(open(f, encoding="utf-8"))
        names = rep["info"]["TeamNames"]
        us = next((i for i, t in enumerate(names) if t == "Farhan Ishraq"), None)
        if us is None:
            continue
        opp_seat = 1 - us
        scores = {c: match(rep, c, opp_seat) for c in cands}
        top = max(scores, key=scores.get)
        rows.append((names[opp_seat][:22], top, scores[top]))
        best[top if scores[top] >= 24 else "none"] += 1
    for team, c, k in rows:
        print(f"  {team:24s} best match {c:34s} prefix {k}")
    print("\nopponent agent identification:", dict(best))
