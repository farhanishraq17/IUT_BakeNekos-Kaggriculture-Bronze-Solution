"""Does the champion leave hands idle? (an idle hand is a free CARE/COLLECT action)

Wraps the agent and compares the number of units it owns against the number it
actually issues ops for, per turn.
"""
import sys, collections
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents

S = collections.Counter()


def probe(agent):
    import inspect
    two = fastsim._takes_config(agent)

    def inner(obs, cfg=None):
        act = agent(obs, cfg) if two else agent(obs)
        farm = (obs.get("farms") or [])[int(obs.get("player") or 0)]
        hands = len(farm.get("hands") or [])
        ops = act.get("hands") or []
        issued = sum(1 for o in ops if o)
        pas = sum(1 for o in ops if o and o[0] == "PASS")
        S["turns"] += 1
        S["hands"] += hands
        S["issued"] += issued
        S["pass_ops"] += pas
        S["missing"] += max(0, hands - len(ops))
        S["orders"] += len(act.get("market") or [])
        f = act.get("farmer") or []
        S["farmer_pass"] += 1 if (not f or f[0] == "PASS") else 0
        return act
    return inner


if __name__ == "__main__":
    cand, opps = sys.argv[1], sys.argv[2].split(",")
    base, n = int(sys.argv[3]), int(sys.argv[4])
    games = 0
    for o in opps:
        opp = opponents.get(o)
        for s in range(base, base + n):
            fastsim.run(probe(opponents.get(cand)), opp, seed=s)
            games += 1
    t = S["turns"]
    print(f"{cand}: {games} games, {t} turns")
    print(f"   hands owned      {S['hands']/t:6.2f} /turn")
    print(f"   ops issued       {S['issued']/t:6.2f} /turn")
    print(f"   of which PASS    {S['pass_ops']/t:6.2f} /turn")
    print(f"   hands with NO op {S['missing']/t:6.2f} /turn")
    print(f"   farmer PASS      {S['farmer_pass']/t:6.1%} of turns")
    print(f"   market orders    {S['orders']/t:6.2f} /turn (cap 10)")
    idle = (S['pass_ops'] + S['missing']) / t
    print(f"   -> IDLE UNIT-ACTIONS {idle:.2f}/turn = {idle*719:.0f}/game")
