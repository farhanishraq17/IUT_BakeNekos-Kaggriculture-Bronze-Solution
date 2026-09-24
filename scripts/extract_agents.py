"""Extract runnable agents from the downloaded public notebooks.

The public lineage embeds its agent three ways: gzip+b64, zlib+b85, or a plain
`%%writefile main.py` cell. Rather than special-case each notebook, try every
decoding of every long literal and keep whatever parses as Python and defines
`agent`. Writes bytes, never text -- several of these notebooks pin a SHA over
their own source including line endings.

    python scripts/extract_agents.py
"""

from __future__ import annotations

import ast
import base64
import gzip
import hashlib
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "opponents" / "notebooks"
OUT = ROOT / "opponents"

DECODERS = [
    ("b64+gzip", lambda s: gzip.decompress(base64.b64decode(s))),
    ("b85+zlib", lambda s: zlib.decompress(base64.b85decode(s))),
    ("b64+zlib", lambda s: zlib.decompress(base64.b64decode(s))),
    ("b85+gzip", lambda s: gzip.decompress(base64.b85decode(s))),
    ("b64", lambda s: base64.b64decode(s)),
]


def is_agent(src: bytes) -> bool:
    if b"def agent" not in src:
        return False
    try:
        compile(src, "<cand>", "exec")
    except SyntaxError:
        return False
    return True


def candidates(text: str):
    """Every long literal in the notebook, via the parser rather than regex.

    The parser folds implicit concatenation (`X = ("aaa" "bbb" ...)`) into one
    constant for free, and lets us join lists of byte chunks -- two patterns the
    public notebooks both use and that no sane regex catches."""
    for m in re.finditer(r"%%writefile\s+\S*main\.py\n(.*?)(?=\n# ---- (?:CODE|MD) ----|\Z)",
                         text, re.S):
        yield m.group(1)

    for cell in text.split("# ---- CODE ----"):
        body = "\n".join(ln for ln in cell.splitlines() if not ln.lstrip().startswith(("%", "!")))
        try:
            tree = ast.parse(body)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)) \
                    and len(node.value) >= 800:
                yield node.value
            elif isinstance(node, (ast.List, ast.Tuple)):
                parts = [e.value for e in node.elts
                         if isinstance(e, ast.Constant) and isinstance(e.value, bytes)]
                if len(parts) == len(node.elts) and parts and sum(map(len, parts)) >= 800:
                    yield b"".join(parts)


def extract(path: Path) -> tuple[str, bytes] | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    best = None
    for cand in candidates(text):
        raw = cand.encode() if isinstance(cand, str) else cand
        if is_agent(raw) and (best is None or len(raw) > len(best[1])):
            best = ("plain", raw)
            continue
        for name, fn in DECODERS:
            try:
                out = fn(cand)
            except Exception:
                continue
            if is_agent(out) and (best is None or len(out) > len(best[1])):
                best = (name, out)
                break
    return best


def main() -> int:
    ok = 0
    for nb in sorted(NB.glob("*.py")):
        got = extract(nb)
        name = nb.stem.replace("kaggriculture-", "").replace("notebookdb6965aa8e", "v54-idle-workers")
        if not got:
            print(f"{name:42s} no embedded agent found")
            continue
        how, raw = got
        dest = OUT / f"{name}.py"
        dest.write_bytes(raw)
        print(f"{name:42s} {how:9s} {len(raw):8,d} B  sha={hashlib.sha256(raw).hexdigest()[:12]}")
        ok += 1
    print(f"\n{ok} agents extracted to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
