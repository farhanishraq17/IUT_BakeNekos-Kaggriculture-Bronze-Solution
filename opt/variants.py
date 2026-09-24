"""One-knob-at-a-time variant sweep on a public base agent (default v50).

pipe-7 went 179-1 by changing one constant; the lineage's own notes say changing
several gears at once breaks the calibrated layers. So: every variant differs
from the base in exactly ONE knob, and is judged head-to-head against the base
and the rest of the panel.

Variants are built two ways:
  - `sub`: exact text substitution of a unique constant in the source
  - `open`: an appended wrapper layer that rewrites the wheat round-trip
    quantities of the first three turns (Kaggle's loader takes the LAST callable,
    which is how every layer in this lineage is attached)

    python opt/variants.py            # full sweep, writes runs/variants.json
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402

BASE = "v50-early-yarn-commit"
VAR_DIR = ROOT / "runs" / "variants"
PANEL = ["v50-early-yarn-commit", "v54-idle-workers", "shop-router-reactive-v7", "fork-2801"]
SEEDS = [31337 + i for i in range(8)]

OPEN_LAYER = '''

# ---- variant layer: opening wheat round-trip quantities -------------------
_VAR_PREV_AGENT = agent
_VAR_OPEN = {open!r}   # {{(step, op): qty}}


def agent(observation, configuration=None):
    act = _VAR_PREV_AGENT(observation, configuration)
    try:
        step = observation["step"]
        if step in (0, 1, 2) and isinstance(act, dict):
            out = []
            for o in act.get("market") or []:
                if isinstance(o, list) and len(o) >= 3 and o[1] == "WHEAT":
                    q = _VAR_OPEN.get((step, o[0]))
                    if q is not None:
                        if q <= 0:
                            continue
                        o = [o[0], o[1], q]
                out.append(o)
            act = dict(act, market=out)
    except Exception:
        pass
    return act
'''


def build(kind: str, spec) -> bytes:
    src = (ROOT / "opponents" / f"{BASE}.py").read_bytes()
    if kind == "base":
        return src
    if kind == "sub":
        old, new = spec
        n = src.count(old.encode())
        if n != 1:
            raise ValueError(f"{old!r} occurs {n} times; substitution must be unique")
        return src.replace(old.encode(), new.encode())
    if kind == "open":
        return src + OPEN_LAYER.format(open=spec).encode()
    raise ValueError(kind)


def materialize(label: str, kind: str, spec) -> str:
    """Write the variant to runs/variants and register it with the loader."""
    raw = build(kind, spec)
    compile(raw, label, "exec")
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha256(raw).hexdigest()[:10]
    path = VAR_DIR / f"var_{tag}.py"
    path.write_bytes(raw)
    return str(path)


def _game(job):
    var_path, opp, seed, swap = job
    me = opponents.get_path(var_path)
    them = opponents.get(opp)
    m = fastsim.run(them, me, seed) if swap else fastsim.run(me, them, seed)
    a, b = (m[1], m[0]) if swap else (m[0], m[1])
    return var_path, opp, (1.0 if a > b else 0.5 if a == b else 0.0), a


# One knob per variant. Base values are v50's own.
SWEEP = [
    ("base", "base", None),
    # Turn-0/1/2 wheat round-trip (v50: buy 7, sell 2, buy 30, sell 30).
    *[(f"open buy0={q}", "open", {(0, "BUY_PRODUCT"): q}) for q in (0, 3, 12, 20, 35)],
    *[(f"open sell0={q}", "open", {(0, "SELL"): q}) for q in (0, 5, 10)],
    *[(f"open buy1={q}", "open", {(1, "BUY_PRODUCT"): q}) for q in (0, 15, 45, 60)],
    *[(f"open sell2={q}", "open", {(2, "SELL"): q}) for q in (0, 15, 45)],
    # Sell-race horizons against clones / mirrors.
    *[(f"race_clone={v}", "sub", ("_RACE_HORIZON_CLONE=8", f"_RACE_HORIZON_CLONE={v}")) for v in (4, 12, 16)],
    *[(f"race_escal={v}", "sub", ("_RACE_HORIZON_ESCALATED=24", f"_RACE_HORIZON_ESCALATED={v}")) for v in (12, 36)],
    *[(f"race_mirror={v}", "sub", ("_RACE_HORIZON_MIRROR=24", f"_RACE_HORIZON_MIRROR={v}")) for v in (12, 36)],
    *[(f"min_sell_price={v}", "sub", ('"min_sell_price": 2,', f'"min_sell_price": {v},')) for v in (1, 4, 8)],
]


KNOBS = {  # knob -> the unique base-value string in v50's source
    "race_escal": "_RACE_HORIZON_ESCALATED=24",
    "race_clone": "_RACE_HORIZON_CLONE=8",
    "race_mirror": "_RACE_HORIZON_MIRROR=24",
}


def main() -> int:
    import argparse
    global SEEDS, PANEL
    ap = argparse.ArgumentParser()
    ap.add_argument("--knob", choices=list(KNOBS), help="confirm mode: sweep one knob")
    ap.add_argument("--values", default="", help="comma list, e.g. 8,12,16")
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--seed-base", type=int, default=SEEDS[0],
                    help="use a FRESH block to confirm -- re-testing on the block a "
                         "variant was selected on is biased toward it")
    ap.add_argument("--panel", default=",".join(PANEL))
    args = ap.parse_args()
    SEEDS = [args.seed_base + i for i in range(args.seeds)]
    PANEL = [p for p in args.panel.split(",") if p]

    sweep = SWEEP
    if args.knob:
        old = KNOBS[args.knob]
        stem = old.split("=")[0]
        sweep = [("base", "base", None)] + [
            (f"{args.knob}={v}", "sub", (old, f"{stem}={v}")) for v in args.values.split(",") if v]

    variants = []
    for label, kind, spec in sweep:
        try:
            variants.append((label, materialize(label, kind, spec)))
        except (ValueError, SyntaxError) as e:
            print(f"skip {label}: {e}")
    jobs = [(p, opp, s, sw) for _l, p in variants for opp in PANEL for s in SEEDS for sw in (False, True)]
    print(f"{len(variants)} variants x {len(PANEL)} opponents x {len(SEEDS)} seeds x 2 seats "
          f"= {len(jobs)} games")
    t = time.time()
    with Pool() as pool:
        res = pool.map(_game, jobs, chunksize=1)
    print(f"done in {time.time()-t:.0f}s\n")

    score = {}
    for path, opp, s, _cash in res:
        score.setdefault(path, {}).setdefault(opp, []).append(s)
    rows = []
    for label, path in variants:
        per = {o: sum(v) / len(v) for o, v in score[path].items()}
        rows.append((label, per, sum(per.values()) / len(per)))

    base = rows[0][1]
    print(f"{'variant':22s}" + "".join(f"{o[:12]:>13s}" for o in PANEL) + "     mean   vs base")
    for label, per, mean in rows:
        cells = "".join(f"{per[o]*100:12.0f}%" for o in PANEL)
        delta = sum(per[o] - base[o] for o in PANEL) / len(PANEL) * 100
        print(f"{label:22s}{cells}   {mean*100:5.1f}%   {delta:+5.1f}")

    (ROOT / "runs" / "variants.json").write_text(json.dumps(
        [{"label": l, "per": p, "mean": m} for l, p, m in rows], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
