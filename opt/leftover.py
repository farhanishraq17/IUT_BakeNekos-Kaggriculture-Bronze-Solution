"""How much value does an agent leave unsold when the season ends?

Unsold stock scores zero. Close losses (tetsutani: 338 of 1065 losses by < $500)
mean every leftover dollar is a potential flipped game. This plays the agent and
reports, at the final state: shed stock, stock still in unit inventories (which
cannot be sold -- SELL only draws from the shed), and its value at final prices.

    python opt/leftover.py c-tetsutani-0921 [opponents...]
"""

from __future__ import annotations

import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def one(job):
    cand, opp, seed = job
    me, them = opponents.get(cand), opponents.get(opp)
    g = fastsim.Game(seed)
    cfg = g.env.configuration
    tw = [fastsim._takes_config(me), fastsim._takes_config(them)]
    for _ in range(719):
        a = me(g.obs(0), cfg) if tw[0] else me(g.obs(0))
        b = them(g.obs(1), cfg) if tw[1] else them(g.obs(1))
        g.step([a, b])
        if g.done:
            break
    o = g.state[0].observation
    priv = g.state[0].observation.private
    prices = o.market["prices"]
    shed = {k: v for k, v in priv["shed"].items() if v and k in PRODUCTS}
    carried = {}
    for inv in priv["inventories"]:
        for k, v in inv.items():
            if k in PRODUCTS and v:
                carried[k] = carried.get(k, 0) + v
    val = lambda d: sum(prices[k] * n for k, n in d.items())  # noqa: E731
    return cand, opp, seed, g.money, val(shed), val(carried), shed, carried


def main(argv):
    cand = argv[0]
    opps = argv[1:] or ["c-koshinm-0921", "shop-router-reactive-v7", "c-wheat-seller", "v50-early-yarn-commit"]
    jobs = [(cand, o, 31337 + i) for o in opps for i in range(4)]
    with Pool() as pool:
        res = pool.map(one, jobs)
    tot_s = tot_c = 0
    for c, o, s, money, vs, vc, shed, carried in res:
        tot_s += vs
        tot_c += vc
        margin = money[0] - money[1]
        print(f"{o:24s} seed {s}  margin {margin:+9,.0f}  unsold shed ${vs:>6,.0f} {shed}  "
              f"carried ${vc:>5,.0f} {carried}")
    print(f"\nmean leftover value per game: shed ${tot_s/len(res):,.0f}, carried ${tot_c/len(res):,.0f}")


if __name__ == "__main__":
    main(sys.argv[1:])
