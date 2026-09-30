"""Knob-screen scoring against a reference candidate.

Per variant: head-to-head win rate vs the reference CONFIG (it sits in the opponent
list), and the paired win-rate delta vs the reference CANDIDATE on identical
(opponent, seed, seat) cells for every other opponent. SEs cluster by seed.

    python runs/screen_report.py REF_NAME file.jsonl [more.jsonl ...]
"""
import collections
import json
import math
import sys


def score(r):
    return 1.0 if r["me"] > r["them"] else 0.5 if r["me"] == r["them"] else 0.0


def clustered(pairs):
    """pairs: list of (seed, value) -> (mean, se, n)"""
    by = collections.defaultdict(list)
    for s, v in pairs:
        by[s].append(v)
    n = sum(len(v) for v in by.values())
    if n == 0:
        return float("nan"), float("nan"), 0
    m = sum(sum(v) for v in by.values()) / n
    k = len(by)
    var = sum((sum(v) - m * len(v)) ** 2 for v in by.values()) / n ** 2 * k / max(1, k - 1)
    return m, math.sqrt(var), n


def main():
    ref = sys.argv[1]
    rows = [json.loads(l) for f in sys.argv[2:] for l in open(f) if l.strip()]
    rows = [r for r in rows if "me" in r]
    cell = {(r["cand"], r["opp"], r["seed"], r["seat"]): score(r) for r in rows}
    cands = sorted({r["cand"] for r in rows})
    opps = sorted({r["opp"] for r in rows})
    # the reference CONFIG as an opponent: strip nothing, it is listed under the same name
    out = []
    for c in cands:
        h2h = clustered([(r["seed"], score(r)) for r in rows if r["cand"] == c and r["opp"] == ref])
        diffs = [(s, cell[(c, o, s, t)] - cell[(ref, o, s, t)])
                 for (cc, o, s, t) in cell if cc == c and o != ref and (ref, o, s, t) in cell]
        d = clustered(diffs) if c != ref else (0.0, 0.0, 0)
        out.append((c, h2h, d))
    print(f"{'variant':52s} {'h2h vs ref cfg':>20s} {'z':>6s} {'paired dWR (others)':>24s} {'z':>6s}")
    key = lambda x: (0 if math.isnan(x[1][0]) else (x[1][0] - 0.5) / max(x[1][1], 1e-9)) + \
                    (0 if not x[2][2] else x[2][0] / max(x[2][1], 1e-9))
    for c, h, d in sorted(out, key=key, reverse=True):
        zh = (h[0] - 0.5) / h[1] if h[2] and h[1] > 0 else float("nan")
        zd = d[0] / d[1] if d[2] and d[1] > 0 else float("nan")
        print(f"{c.replace('guard:c-pi-0927', 'pi')[:52]:52s} {h[0]:8.1%} ±{h[1]:4.1%} n={h[2]:<5d}{zh:6.2f} "
              f"{d[0]:+9.2%} ±{d[1]:4.1%} n={d[2]:<5d}{zd:6.2f}")


if __name__ == "__main__":
    main()
