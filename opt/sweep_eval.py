"""One-knob sweep of a base agent, analysed as PAIRED comparisons.

Every variant plays exactly the same (seed, opponent, seat) games as the base,
so the per-game difference is zero wherever the knob never fires. Only games
where behaviour changed add noise, which is what makes a 1-2 point effect
detectable at all.

    python opt/sweep_eval.py knobs              # print the candidate list for --cands
    python opt/sweep_eval.py analyse runs/sw_all.jsonl [more.jsonl]
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

BASE = "c-tetsutani-0921@_SR_MARGIN=12@_Y_MARGIN=-12"
# Round 1 (submitted 2026-09-22, see PLAN.md): _SR_MARGIN 8->12 and _Y_MARGIN -6->-12
# confirmed across 3 independent seed ranges (211k games), baked into runs/sub_tetsutani_tuned.
# Round 2: new constants not covered by round 1, same paired-sweep method.
KNOBS = {  # knob -> alternative values (base value in comment)
    "_CA_MARGIN": [-10.0, 5.0],           # -5.0; carrot-vs-wheat swap profitability gate
    "_CA_BUFFER": [4, 12],                # 8; reserve quantity for that swap
    "_OR2_CAP": [20, 40],                 # 30; order-routing exposure cap
    "_OR2_SLOT_MARGIN": [10.0, 30.0],     # 20.0; slot-replacement margin
    "V9_RACEPX_MARGIN": [-5, 5],          # 0; race price-gate margin
    "V9_RACEGATE_MARGIN": [-5, 5],        # 0; race gate margin
    "V9_RACE_MAX": [40, 60],              # 48; race horizon ceiling
    "_HD2_RATIO": [1.1, 1.5],             # 1.3
    "_HD2_CARE": [0.5, 1.0],              # 0.8
    "_HD2_FUTURE": [0.3, 0.6],            # 0.0
    "_CS_RATIO": [1.1, 1.5],              # 1.3
    "_HD2_LOOKBACK": [1, 5],              # 3
}


def candidates():
    return [BASE] + [f"{BASE}@{k}={v}" for k, vs in KNOBS.items() for v in vs]


def score(r):
    return 1.0 if r["me"] > r["them"] else 0.5 if r["me"] == r["them"] else 0.0


def analyse(paths):
    rows = []
    for p in paths:
        if Path(p).exists():
            rows += [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]
    rows = [r for r in rows if "error" not in r]
    base = {(r["seed"], r["opp"], r["seat"]): score(r) for r in rows if r["cand"] == BASE}
    by = defaultdict(list)
    for r in rows:
        if r["cand"] != BASE:
            k = (r["seed"], r["opp"], r["seat"])
            if k in base:
                by[r["cand"]].append(score(r) - base[k])
    print(f"{len(rows)} games; base played {len(base)} (seed, opp, seat) cells\n")
    print(f"{'variant':46s} {'paired n':>8s} {'changed':>8s} {'delta':>8s} {'z':>6s}")
    out = []
    for cand, d in by.items():
        n = len(d)
        mean = sum(d) / n
        var = sum((x - mean) ** 2 for x in d) / max(1, n - 1)
        se = math.sqrt(var / n) if var > 0 else 0.0
        z = mean / se if se else 0.0
        out.append((z, cand, n, sum(1 for x in d if x != 0), mean))
    for z, cand, n, changed, mean in sorted(out, reverse=True):
        flag = "  <-- candidate" if z >= 2.5 else ""
        print(f"{cand.split('@', 1)[1]:46s} {n:8d} {changed:8d} {mean * 100:+7.2f}p {z:6.2f}{flag}")
    print("\nz >= 2.5 on a 30-variant sweep is the bar (multiple comparisons); anything flagged must be"
          "\nre-confirmed on a FRESH seed block before it is submitted.")


if __name__ == "__main__":
    if sys.argv[1] == "knobs":
        print(",".join(candidates()))
    else:
        analyse(sys.argv[2:])
