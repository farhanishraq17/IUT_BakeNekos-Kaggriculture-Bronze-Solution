"""Paired comparison of every candidate against a named base, from worldeval jsonl.

    python opt/paired.py BASE file1.jsonl [file2.jsonl ...] [--only SUBSTR]
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def score(r):
    return 1.0 if r["me"] > r["them"] else 0.5 if r["me"] == r["them"] else 0.0


def main(argv):
    base, *rest = argv
    only = None
    if "--only" in rest:
        i = rest.index("--only")
        only = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]
    rows = []
    for p in rest:
        if Path(p).exists():
            rows += [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
    rows = [r for r in rows if "error" not in r]
    b = {(r["seed"], r["opp"], r["seat"]): score(r) for r in rows if r["cand"] == base}
    by = defaultdict(list)
    raw = defaultdict(list)
    for r in rows:
        raw[r["cand"]].append(score(r))
        if r["cand"] != base and (only is None or only in r["cand"]):
            k = (r["seed"], r["opp"], r["seat"])
            if k in b:
                by[r["cand"]].append(score(r) - b[k])
    print(f"{len(rows)} games; base {base} win {sum(raw[base])/max(1,len(raw[base]))*100:.1f}% ({len(b)} cells)\n")
    out = []
    for c, d in by.items():
        n = len(d)
        m = sum(d) / n
        v = sum((x - m) ** 2 for x in d) / max(1, n - 1)
        se = math.sqrt(v / n) if v > 0 else 0
        out.append((m / se if se else 0.0, c, n, m, sum(raw[c]) / len(raw[c])))
    for z, c, n, m, wr in sorted(out, reverse=True):
        print(f"{c[-60:]:60s} n={n:5d} win={wr*100:5.1f}% delta={m*100:+6.2f}p z={z:6.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
