"""At which step do two agents first act differently in the SAME game?

A cross-family router can only switch while both candidates are still emitting
identical actions -- after that, the loser's tape has missed moves it assumes it
made. This measures that window.
"""
import sys, json
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents

def canon(a):
    return json.dumps(a, sort_keys=True, default=str)

def first_divergence(a_name, b_name, opp_name, seed):
    A, B = opponents.get(a_name), opponents.get(b_name)
    opp = opponents.get(opp_name)
    ta, tb, to = (fastsim._takes_config(x) for x in (A, B, opp))
    g = fastsim.Game(seed, {"episodeSteps": 720})
    cfg = g.env.configuration
    for t in range(719):
        obs0, obs1 = g.obs(0), g.obs(1)
        a = A(obs0, cfg) if ta else A(obs0)
        b = B(obs0, cfg) if tb else B(obs0)
        if canon(a) != canon(b):
            return t
        o = opp(obs1, cfg) if to else opp(obs1)
        g.step([a, o])
        if g.done:
            break
    return 719

if __name__ == "__main__":
    a, b, opps = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
    base, n = int(sys.argv[4]), int(sys.argv[5])
    out = []
    for o in opps:
        for s in range(base, base + n):
            out.append(first_divergence(a, b, o, s))
    out.sort()
    print(f"{a}  vs  {b}")
    print(f"  first divergence step: min {out[0]}, median {out[len(out)//2]}, max {out[-1]}  (n={len(out)})")
