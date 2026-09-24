"""Watch a public agent play and write down its strategy.

Reverse-engineering their route-tape encoding is the slow way. Running one and
logging what it actually does per day -- hires, purchases, plantings, sale timing
-- gives the recipe directly, and the recipe is what we need to encode.

    python opt/analyze.py v50-early-yarn-commit
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402


def analyze(name: str, opp: str = "starter", seed: int = 4242):
    subject = opponents.get(name)
    other = opponents.get(opp)

    per_day = defaultdict(lambda: {"orders": Counter(), "units": Counter(),
                                   "sell_hours": Counter(), "spend": Counter()})
    sells = []          # (day, hour, item, qty)
    money_at_day = {}

    def watched(obs):
        a = subject(obs)
        d, h = obs["day"], obs["hour"]
        rec = per_day[d]
        for o in (a.get("market") or []):
            if not isinstance(o, list) or not o:
                continue
            op = o[0]
            rec["orders"][op] += 1
            if op == "SELL" and len(o) >= 3:
                rec["sell_hours"][h] += 1
                sells.append((d, h, o[1], o[2]))
            elif op in ("BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT") and len(o) >= 3:
                rec["spend"][f"{op[4:]}:{o[1]}"] += int(o[2]) if str(o[2]).lstrip("-").isdigit() else 1
        for u in [a.get("farmer")] + list(a.get("hands") or []):
            if isinstance(u, list) and u:
                rec["units"][u[0] if len(u) == 1 or u[0] not in ("PLANT", "PICKUP", "PLACE")
                             else f"{u[0]}:{u[1]}"] += 1
        return a

    g = fastsim.Game(seed, {"episodeSteps": 720})
    for _ in range(719):
        g.step([watched(g.obs(0)), other(g.obs(1))])
        if g.done:
            break
        o = g.state[0].observation
        if o.hour == 12:
            money_at_day[o.day] = o.farms[0]["money"]

    obs = g.state[0].observation
    farm = obs.farms[0]
    print(f"=== {name}  vs {opp}  seed {seed}   final ${farm['money']:,.0f}")
    print(f"    shops this season: {obs.town['unlocked_shops']}")

    print("\nday  money      hires  land  tiles(crops/animals)                     top unit ops")
    for d in range(30):
        rec = per_day[d]
        tiles = ""
        if d in money_at_day:
            pass
        ops = ", ".join(f"{k}x{v}" for k, v in rec["units"].most_common(4))
        buys = ", ".join(f"{k}x{v}" for k, v in rec["spend"].most_common(4))
        print(f"{d:3d}  ${money_at_day.get(d, 0):9,.0f}  {rec['orders']['HIRE']:5d}  "
              f"{rec['orders']['BUY_LAND']:4d}  {buys[:40]:40s}  {ops[:46]}")

    print("\nfinal farm composition:")
    comp = Counter()
    for row in farm["tiles"]:
        for t in row:
            if t is None:
                comp["empty"] += 1
            elif t == "LOCKED":
                comp["LOCKED"] += 1
            elif t.get("kind") == "PLANT":
                comp[t["crop"]] += 1
            elif "animal" in t:
                comp[t["animal"]] += 1
            else:
                comp[t["kind"] + "(empty)"] += 1
    print("   ", dict(comp.most_common()))

    print("\nsales by item (units, and the day they start):")
    by_item = defaultdict(lambda: [0, 99])
    for d, _h, item, qty in sells:
        q = int(qty) if str(qty).lstrip("-").isdigit() else 0
        by_item[item][0] += q
        by_item[item][1] = min(by_item[item][1], d)
    for item, (q, d0) in sorted(by_item.items(), key=lambda kv: -kv[1][0]):
        print(f"    {item:12s} {q:6d} units, first sold day {d0}")

    hours = Counter(h for _d, h, _i, _q in sells)
    print("\nsale orders by hour of day (town shops consume at hour%4==0, town centre at hour 0):")
    print("   ", " ".join(f"{h}:{hours.get(h,0)}" for h in range(24)))

    total_hires = sum(per_day[d]["orders"]["HIRE"] for d in range(30))
    print(f"\ntotal HIRE orders: {total_hires}  (avg {total_hires/30:.1f}/day)")


if __name__ == "__main__":
    analyze(*(sys.argv[1:] or ["pipe-7-wheat-microstructure"]))
