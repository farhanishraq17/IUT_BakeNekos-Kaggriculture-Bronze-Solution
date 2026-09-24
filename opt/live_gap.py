"""Where do we lose money in live losses? Per-product sale revenue, us vs opponent,
reconstructed from replays (shed decrease on SELL turns x pre-market price), plus
spend on seeds/animals/hires/land/buy-product.

    python opt/live_gap.py data/our_episodes "Farhan Ishraq"
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def analyse(path):
    d = json.load(open(path, encoding="utf-8"))
    st = d["steps"]
    res = []
    for p in (0, 1):
        rev = defaultdict(float)
        for t in range(len(st) - 1):
            o = st[t][p].get("observation") or {}
            o1 = st[t + 1][p].get("observation") or {}
            a = st[t + 1][p].get("action") or {}
            prices = (st[t][0].get("observation") or {}).get("market", {}).get("prices", {})
            sh0 = (o.get("private") or {}).get("shed", {}) or {}
            sh1 = (o1.get("private") or {}).get("shed", {}) or {}
            for od in a.get("market") or []:
                if isinstance(od, list) and len(od) >= 2 and od[0] == "SELL" and od[1] in PRODUCTS:
                    n = int(sh0.get(od[1], 0)) - int(sh1.get(od[1], 0))
                    if n > 0:
                        rev[od[1]] += n * int(prices.get(od[1], 0))
        res.append(rev)
    rewards = [s.get("reward") for s in st[-1]]
    return d["info"]["TeamNames"], rewards, res


def main(folder, me):
    gap_loss = defaultdict(float)
    gap_win = defaultdict(float)
    nl = nw = 0
    for f in glob.glob(f"{folder}/*.json"):
        try:
            names, rew, res = analyse(f)
        except Exception:
            continue
        if me not in names or rew[0] is None:
            continue
        us = names.index(me)
        them = 1 - us
        tgt = gap_loss if rew[us] < rew[them] else gap_win
        if rew[us] < rew[them]:
            nl += 1
        else:
            nw += 1
        for it in PRODUCTS:
            tgt[it] += res[them][it] - res[us][it]
    print(f"losses {nl}, wins {nw}")
    print(f"{'product':12s} {'opp-us rev in LOSSES (mean)':>28s} {'in WINS (mean)':>16s}")
    for it in PRODUCTS:
        print(f"{it:12s} {gap_loss[it]/max(1,nl):28.0f} {gap_win[it]/max(1,nw):16.0f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
