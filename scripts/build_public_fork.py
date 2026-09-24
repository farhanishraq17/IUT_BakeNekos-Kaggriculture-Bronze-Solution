"""Rebuild the public 2801-rated agent exactly, byte-for-byte.

The notebook's rating came from V44 PLUS four wrapper layers, not from V44 alone
(its own text says plain V44 plateaus around 2630). This reproduces the
documented assembly and asserts the notebook's published sha256, so a clean run
means we have exactly the file that scored on the live ladder.

  USE_CADENCE False -> V44 + layers 1, 2, 4   (live submission 56277542, rating 2801)
  USE_CADENCE True  -> V44 + layers 1, 2, 3, 4 (live submission 56280605)

Apache-2.0. Upstream notices in the source are retained verbatim, as the licence
requires -- see the attribution header of the produced file.

    python scripts/build_public_fork.py [--cadence]
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "opponents" / "notebooks" / "kaggriculture-2820-score.py"
OUT = ROOT / "agents" / "public_fork_main.py"

EXPECTED_SHA256 = {
    True: "fa9e47d81de5020847c1dbc7ca10d058b227be66deea7c019040fb12a1d99f19",
    False: "016b9a32248f34477cf5f153119d6f361c39d99a50734e435ac2860f65493fe7",
}

# (newline, leading blank lines, trailing blank lines) -- from the notebook's
# build cell. %%writefile does not preserve the live file's mixed line endings,
# so each layer is normalised to LF, stripped, then restored from this table.
LAYER_FORMAT = {
    "layer1_preguard": ("\n", 1, 2),
    "layer2_lockstep": ("\r\n", 1, 1),
    "layer3_cadence": ("\n", 2, 1),
    "layer4_yarnherd": ("\r\n", 1, 1),
}


def notebook_text() -> str:
    return NB.read_text(encoding="utf-8", errors="replace")


def v44_base(text: str) -> bytes:
    m = re.search(r"V44_GZ_B64 = \(\s*((?:\s*\"[^\"]*\"\s*)+)\)", text)
    if not m:
        raise SystemExit("could not find V44_GZ_B64")
    blob = "".join(re.findall(r'"([^"]*)"', m.group(1)))
    return gzip.decompress(base64.b64decode(blob))


def layer_bytes(text: str, name: str) -> bytes:
    newline, lead, trail = LAYER_FORMAT[name]
    m = re.search(r"%%writefile\s+build/" + re.escape(name) + r"\.py\n(.*?)"
                  r"(?=\n# ---- (?:CODE|MD) ----|\Z)", text, re.S)
    if not m:
        raise SystemExit(f"could not find cell for {name}")
    body = m.group(1).replace("\r", "").strip("\n")
    return ("\n" * lead + body + "\n" * trail).replace("\n", newline).encode("utf-8")


def main() -> int:
    use_cadence = "--cadence" in sys.argv
    text = notebook_text()

    source = v44_base(text)
    print(f"  v44_base          {len(source):9,d} bytes")

    names = ["layer1_preguard", "layer2_lockstep"]
    if use_cadence:
        names.append("layer3_cadence")
    names.append("layer4_yarnherd")
    for name in names:
        part = layer_bytes(text, name)
        source += part
        print(f"  {name:18s}{len(part):9,d} bytes")

    sha = hashlib.sha256(source).hexdigest()
    want = EXPECTED_SHA256[use_cadence]
    print(f"\n  sha256 {sha}")
    print(f"  want   {want}")
    if sha != want:
        print("\nMISMATCH -- this is NOT the file that scored on the ladder. Not writing.")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(source)
    print(f"\nMATCH. wrote {OUT} ({len(source):,} bytes)")
    print("build:", "V44 + layers 1,2,3,4" if use_cadence else "V44 + layers 1,2,4 (rating 2801)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
