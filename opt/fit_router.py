"""Fit a shop-conditional route table from world-eval games, and measure it honestly.

For each opening family, every candidate played the SAME (seed, opponent, seat)
games, so candidates are compared paired, game by game. A world (sorted pair of
the first two shops) is routed away from the default only when a candidate beats
the default there by a margin on enough paired games.

Choosing the per-world winner on the data you score it on overstates the gain,
so the reported number is 2-fold cross-validated over seeds.

    python opt/fit_router.py runs/we_all.jsonl runs/we/local/we.jsonl
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

FAMILIES = {
    "H": ["c-tetsutani-0921", "c-wheat-seller", "c-one-more-wheat"],
    "K": ["c-koshinm-0921", "c-koshinm-0920"],
}
MIN_N = 16        # paired games in a world before it may be routed
MARGIN = 0.06     # candidate must beat the default by this much in that world


def score(r):
    return 1.0 if r["me"] > r["them"] else 0.5 if r["me"] == r["them"] else 0.0


def world(r):
    return "|".join(sorted(r["shops"][:2]))


def load(paths):
    rows = []
    for p in paths:
        if Path(p).exists():
            for line in Path(p).read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    if "error" not in r and r.get("shops"):
                        rows.append(r)
    return rows


def paired(rows, fam):
    """(seed, opp, seat) -> {cand: score}, only for games every candidate played."""
    g = defaultdict(dict)
    w = {}
    for r in rows:
        if r["cand"] in fam:
            k = (r["seed"], r["opp"], r["seat"])
            g[k][r["cand"]] = score(r)
            w[k] = world(r)
    return {k: v for k, v in g.items() if len(v) == len(fam)}, w


def fit(games, worlds, fam):
    default = fam[0]
    by_w = defaultdict(list)
    for k, v in games.items():
        by_w[worlds[k]].append(v)
    table = {}
    for w, vs in by_w.items():
        if len(vs) < MIN_N:
            continue
        base = sum(v[default] for v in vs) / len(vs)
        best = max(fam, key=lambda c: sum(v[c] for v in vs) / len(vs))
        gain = sum(v[best] for v in vs) / len(vs) - base
        if best != default and gain >= MARGIN:
            table[w] = best
    return table


def evaluate(games, worlds, table, fam):
    if not games:
        return 0.0, 0.0, 0
    d = sum(v[fam[0]] for v in games.values()) / len(games)
    r = sum(v[table.get(worlds[k], fam[0])] for k, v in games.items()) / len(games)
    return d, r, len(games)


def main(paths) -> int:
    rows = load(paths)
    seeds = sorted({r["seed"] for r in rows})
    print(f"{len(rows)} games, {len(seeds)} seeds\n")

    print("overall win rate vs the panel, per candidate:")
    agg = defaultdict(list)
    for r in rows:
        agg[r["cand"]].append(score(r))
    for c, v in sorted(agg.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        print(f"  {c:20s} {sum(v)/len(v)*100:5.1f}%  ({len(v)} games)")

    for name, fam in FAMILIES.items():
        games, worlds = paired(rows, fam)
        if not games:
            continue
        # 2-fold CV over seeds: fit on one half, score on the other, both ways.
        folds = [{s for i, s in enumerate(seeds) if i % 2 == f} for f in (0, 1)]
        cv_d = cv_r = n_tot = 0.0
        for f in (0, 1):
            train = {k: v for k, v in games.items() if k[0] not in folds[f]}
            test = {k: v for k, v in games.items() if k[0] in folds[f]}
            t = fit(train, worlds, fam)
            d, r, n = evaluate(test, worlds, t, fam)
            cv_d += d * n
            cv_r += r * n
            n_tot += n
        full = fit(games, worlds, fam)
        oracle = sum(max(v.values()) for v in games.values()) / len(games)
        print(f"\nfamily {name} {fam}  ({len(games)} paired games)")
        print(f"  default {fam[0]:18s} {cv_d/n_tot*100:5.1f}%")
        print(f"  router (2-fold CV)          {cv_r/n_tot*100:5.1f}%   gain {(cv_r-cv_d)/n_tot*100:+.1f} pts")
        print(f"  per-game oracle (ceiling)   {oracle*100:5.1f}%   <- unreachable, for scale only")
        print(f"  routed worlds in final table: {len(full)}")
        Path(f"runs/route_{name}.json").write_text(json.dumps(full, indent=1, sort_keys=True))

    # Where does our live submission lose? Worst worlds for koshinm-0921.
    kw = defaultdict(list)
    for r in rows:
        if r["cand"] == "c-koshinm-0921":
            kw[world(r)].append(score(r))
    worst = sorted(((sum(v) / len(v), len(v), w) for w, v in kw.items() if len(v) >= 10))[:8]
    if worst:
        print("\nkoshinm-0921's weakest shop worlds (first two shops):")
        for wr, n, w in worst:
            print(f"  {w:34s} {wr*100:5.1f}%  ({n} games)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["runs/we_all.jsonl", "runs/we/local/we.jsonl"]))
