"""Pull public competition notebooks via the authenticated CLI and flatten them to
opponents/notebooks/<slug>.py (the cell-marker format extract_agents.py reads).

    python scripts/fetch_notebooks.py owner/slug [owner/slug ...]
"""

from __future__ import annotations

import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kfarm import kag, live_accounts  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "opponents" / "notebooks"


def flatten(nb: dict) -> str:
    out = []
    for c in nb.get("cells", []):
        src = "".join(c.get("source", []))
        if c.get("cell_type") == "markdown":
            out.append("# ---- MD ----\n" + "\n".join("# " + ln for ln in src.splitlines()))
        else:
            out.append("# ---- CODE ----\n" + src)
    return "\n\n".join(out)


def fetch(ref: str, alias: str, token: str) -> str:
    slug = ref.split("/", 1)[1]
    with tempfile.TemporaryDirectory() as td:
        r = kag(alias, token, "kernels", "pull", ref, "-p", td, timeout=300)
        files = list(Path(td).iterdir())
        if not files:
            return f"FAIL {ref}: {(r.stdout + r.stderr).strip()[:120]}"
        f = max(files, key=lambda p: p.stat().st_size)
        if f.suffix == ".ipynb":
            text = flatten(json.loads(f.read_text(encoding="utf-8")))
        else:
            text = "# ---- CODE ----\n" + f.read_text(encoding="utf-8", errors="replace")
    (OUT / f"{slug}.py").write_text(text, encoding="utf-8")
    return f"ok   {ref:70s} {len(text):>9,d} chars"


def main(refs: list[str]) -> int:
    alias = "ISHRAQ"
    _u, token = live_accounts()[alias]
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        for line in ex.map(lambda r: fetch(r, alias, token), refs):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
