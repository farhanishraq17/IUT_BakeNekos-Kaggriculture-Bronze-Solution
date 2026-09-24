"""Bake one or more KNOB=VALUE substitutions permanently into a base agent file,
for submission. Unlike opt/opponents.py's runtime "@" variants (used only for
paired evaluation), this writes a real standalone main.py with an attribution
header noting the tuning, keeping all upstream notices intact.

    python scripts/bake_variant.py c-tetsutani-0921 _RACE_HORIZON_ESCALATED=12 \
        --out runs/sub_tetsutani_tuned/main.py
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HEADER_TMPL = '''# ---- tuning note (added {when}) --------------------------------------------
# The base agent below is unmodified except for {n} constant(s), each re-tuned
# by a paired one-knob-at-a-time sweep against a {panel_n}-agent panel and
# confirmed on a held-out seed block (see opt/sweep_eval.py, PLAN.md).
{changes}
# All original upstream notices in the source below are retained verbatim.
# ------------------------------------------------------------------------------

'''


def bake(base: str, subs: list[str]) -> str:
    path = ROOT / "opponents" / f"{base}.py"
    src = path.read_text(encoding="utf-8")
    changes = []
    for s in subs:
        knob, value = s.split("=", 1)
        pat = re.compile(rf"^{re.escape(knob)}[ \t]*=[ \t]*[^\n]*$", re.M)
        hits = pat.findall(src)
        if len(hits) != 1:
            raise SystemExit(f"{knob!r} matched {len(hits)} lines in {base}; need exactly 1")
        old = hits[0]
        src = pat.sub(f"{knob} = {value}", src, count=1)
        changes.append(f"#   {knob}: {old.split('=',1)[1].strip()} -> {value}")
    header = HEADER_TMPL.format(when=time.strftime("%Y-%m-%d"), n=len(subs),
                                panel_n="12", changes="\n".join(changes))
    return header + src


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("subs", nargs="+", help="KNOB=VALUE")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(bake(args.base, args.subs), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
