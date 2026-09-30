"""Win-rate report for a farm round: candidates x opponents, seed-clustered SEs.

Mirror-ish games give the same result from both seats, so the independent unit
is the seed, not the game: SEs here cluster by seed (games of one candidate on
one seed form one cluster).

    python runs/rr_report.py runs/n28_all.jsonl [--field a,b,c] [--family x,y] [--matrix]
"""
import collections
import json
import math
import sys


def score(r):
    return 1.0 if r["me"] > r["them"] else 0.5 if r["me"] == r["them"] else 0.0


def clustered(rows):
    """mean and seed-clustered SE of the score."""
    by_seed = collections.defaultdict(list)
    for r in rows:
        by_seed[r["seed"]].append(score(r))
    n = sum(len(v) for v in by_seed.values())
    if n == 0:
        return float("nan"), float("nan"), 0
    m = sum(sum(v) for v in by_seed.values()) / n
    k = len(by_seed)
    var = sum((sum(v) - m * len(v)) ** 2 for v in by_seed.values()) / n ** 2 * k / max(1, k - 1)
    return m, math.sqrt(var), n


def main():
    path = sys.argv[1]
    args = sys.argv[2:]
    opt = {a: args[i + 1] for i, a in enumerate(args) if a.startswith("--") and i + 1 < len(args)}
    rows = [json.loads(l) for l in open(path) if l.strip()]
    errs = [r for r in rows if "me" not in r]
    rows = [r for r in rows if "me" in r]
    cands = sorted({r["cand"] for r in rows})
    opps = sorted({r["opp"] for r in rows})
    print(f"{len(rows):,} games, {len(errs)} errors, {len({r['seed'] for r in rows})} seeds")
    if errs:
        print("  first error:", errs[0])
    groups = {"ALL": set(opps)}
    if "--field" in opt:
        groups["FIELD"] = set(opt["--field"].split(","))
    if "--family" in opt:
        groups["FAMILY"] = set(opt["--family"].split(","))
    hdr = "".join(f"{g:>22s}" for g in groups)
    print(f"{'candidate':40s}{hdr}")
    res = []
    for c in cands:
        cells = []
        for g, members in groups.items():
            m, se, n = clustered([r for r in rows if r["cand"] == c and r["opp"] in members])
            cells.append(f"{m:8.1%} ±{se:5.1%} n={n:<5d}")
        res.append((c, cells))
    for c, cells in sorted(res, key=lambda x: x[1][-1], reverse=True):
        print(f"{c:40s}" + "".join(f"{x:>22s}" for x in cells))
    if "--matrix" in args:
        print()
        short = {o: o.replace("guard:", "g:").replace("c-", "")[:14] for o in opps}
        print(f"{'':34s}" + "".join(f"{short[o]:>15s}" for o in opps))
        for c in cands:
            line = f"{c.replace('guard:', 'g:')[:34]:34s}"
            for o in opps:
                m, se, n = clustered([r for r in rows if r["cand"] == c and r["opp"] == o])
                line += f"{'' if n == 0 else f'{m:6.1%}({n})':>15s}"
            print(line)


if __name__ == "__main__":
    main()
