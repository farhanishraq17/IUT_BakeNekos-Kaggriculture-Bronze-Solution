"""Per-product sales and prices through one head-to-head game.

Revenue per product is reconstructed from shed decreases on turns where a SELL
was issued, valued at that product's pre-market price. It is an estimate (the
lockstep resolution moves the price unit by unit), which is fine for finding
WHICH product one agent is losing to the other.

    python opt/duel_trace.py c-tetsutani-0921 shop-router-reactive-v7 31337
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def trace(a_name, b_name, seed):
    agents = [opponents.get(a_name), opponents.get(b_name)]
    tw = [fastsim._takes_config(x) for x in agents]
    g = fastsim.Game(seed)
    cfg = g.env.configuration
    rev = [defaultdict(float), defaultdict(float)]
    units = [defaultdict(int), defaultdict(int)]
    first_sale = [dict(), dict()]
    prices_by_day = {}
    for _ in range(719):
        o = g.state[0].observation
        pre_prices = dict(o.market["prices"])
        pre_shed = [dict(g.state[p].observation.private["shed"]) for p in (0, 1)]
        acts = [agents[p](g.obs(p), cfg) if tw[p] else agents[p](g.obs(p)) for p in (0, 1)]
        g.step(acts)
        for p in (0, 1):
            sold_items = {x[1] for x in (acts[p].get("market") or []) if isinstance(x, list) and x and x[0] == "SELL"}
            post = g.state[p].observation.private["shed"]
            for it in sold_items:
                if it in PRODUCTS:
                    n = pre_shed[p].get(it, 0) - post.get(it, 0)
                    if n > 0:
                        units[p][it] += n
                        rev[p][it] += n * pre_prices[it]
                        first_sale[p].setdefault(it, o.day)
        if o.hour == 0:
            prices_by_day[o.day] = pre_prices
        if g.done:
            break
    return g.money, rev, units, first_sale, prices_by_day, g.state[0].observation.town["unlocked_shops"]


def main(a, b, seed):
    money, rev, units, first, prices, shops = trace(a, b, int(seed))
    print(f"{a} ${money[0]:,.0f}  vs  {b} ${money[1]:,.0f}   shops {shops}\n")
    print(f"{'product':11s} {'A units':>8s} {'A rev':>9s} {'A day1':>6s} | {'B units':>8s} {'B rev':>9s} {'B day1':>6s} | {'B-A rev':>9s}")
    for it in PRODUCTS:
        ra, rb = rev[0][it], rev[1][it]
        if units[0][it] or units[1][it]:
            print(f"{it:11s} {units[0][it]:8d} {ra:9,.0f} {first[0].get(it, '-'):>6} | "
                  f"{units[1][it]:8d} {rb:9,.0f} {first[1].get(it, '-'):>6} | {rb - ra:+9,.0f}")
    print("\nprices at hour 0, days 5/10/15/20/25/29:")
    for it in ("WOOL", "MILK", "STRAWBERRY", "MELON", "FERTILIZER", "WHEAT", "EGG"):
        print(f"  {it:11s} " + "  ".join(f"{prices.get(d, {}).get(it, '-'):>5}" for d in (5, 10, 15, 20, 25, 29)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
