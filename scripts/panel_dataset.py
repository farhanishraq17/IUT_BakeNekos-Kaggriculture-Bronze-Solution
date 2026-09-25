"""Package the evaluation panel as a PRIVATE Kaggle dataset on every farm account.

Kernels can only mount datasets their own account can see, so each account gets
its own private copy. Files are the unmodified agents (Apache-2.0 notices
untouched); nothing is published.

    python scripts/panel_dataset.py            # create, or new version if it exists
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kfarm import kag, live_accounts  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SLUG = "kagri-panel"

# One representative per behaviour family (identical tournament rows = one family):
# v54-idle-workers = c-2965 = c-tetsutani-0920 ; c-v53 = c-v52 ; c-one-more-wheat = c-v54-productive.
PANEL = [
    "c-koshinm-0921", "c-koshinm-0920", "c-tetsutani-0921", "c-wheat-seller", "c-one-more-wheat",
    "c-v53", "v50-early-yarn-commit", "shop-router-reactive-v7", "v54-idle-workers",
    "c-anhad-metav4", "c-wonderful", "c-2950",
    # 2026-09-22 new public builds (kernel outputs, exact submitted files)
    "c-tetsutani-0922", "c-frontier-0922", "c-harvest-ledger", "c-dmitrii-2700", "c-more-wheat-ss-0922", "c-k0013",
    # 2026-09-23/24 builds
    "c-frontier-0923", "c-harvest-ledger-0923", "c-herdsafe-v3", "c-herdsafe-ca25",
    "c-pop-robust", "c-shepherds-ledger", "c-v15stack", "c-late-v16", "c-thomas-2944",
    # 2026-09-24 builds
    "c-masterhybrid-2965", "c-shepherds-0924", "c-harvest-ledger-0924", "c-pop-robust-0924",
    "c-pioneers-c2", "c-cha22",
    "c-evgen-0924", "c-utils-v1", "c-icefire-0925",
]


def stage(dst: Path, username: str) -> None:
    for name in PANEL:
        src = ROOT / "opponents" / f"{name}.py"
        if src.exists():
            shutil.copyfile(src, dst / f"{name}.py")
        elif (ROOT / "opponents" / name).is_dir():
            shutil.copytree(ROOT / "opponents" / name, dst / name,
                            ignore=shutil.ignore_patterns("__pycache__"))
        else:
            raise SystemExit(f"missing panel member {name}")
    (dst / "PANEL_MANIFEST.json").write_text(json.dumps({"panel": PANEL}, indent=1))
    (dst / "dataset-metadata.json").write_text(json.dumps({
        "title": SLUG, "id": f"{username}/{SLUG}", "licenses": [{"name": "other"}],
    }))


def upload(alias: str, username: str, token: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        stage(d, username)
        r = kag(alias, token, "datasets", "create", "-p", str(d), "-q", timeout=1800)
        out = (r.stdout + r.stderr).strip()
        if "already" in out.lower() or "exists" in out.lower():
            r = kag(alias, token, "datasets", "version", "-p", str(d), "-m", "panel refresh", "-q",
                    timeout=1800)
            out = (r.stdout + r.stderr).strip()
    return f"{alias:8s} {username}/{SLUG}: {out[-160:]}"


def main() -> int:
    live = live_accounts()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for line in ex.map(lambda a: upload(a, *live[a]), sorted(live)):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
