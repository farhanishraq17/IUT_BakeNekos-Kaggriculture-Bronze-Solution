"""Build a shop-conditional router over agents that share an opening.

Every candidate is run on every turn until the decision step, so each keeps the
internal state it would have had on its own. At DECIDE_STEP (two shops known) the
router picks a candidate from the route table -- but ONLY one whose actions have
matched the default's on every step so far. Handing control to an agent whose
opening diverged would leave it running a plan for a farm it did not build.

Candidates are embedded unmodified (Apache-2.0 notices intact) in separate
namespaces; this file adds only the routing shim and an attribution header.

    python scripts/build_router.py --cands a,b,c --table runs/route.json --out agents/router/main.py
"""

from __future__ import annotations

import argparse
import base64
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SHIM = r'''
# ---------------------------------------------------------------- routing shim
import base64 as _b64, lzma as _lz, json as _json

_SOURCES = {sources}
_ROUTE = {route}          # "SHOP_A|SHOP_B" (sorted) -> candidate name
_DEFAULT = {default!r}
_DECIDE_STEP = {decide}


def _load(name):
    ns = {{"__name__": "cand_" + name.replace("-", "_")}}
    exec(compile(_lz.decompress(_b64.b85decode(_SOURCES[name])).decode("utf-8"), name, "exec"), ns)
    return ns["agent"]


_AGENTS = {{n: _load(n) for n in _SOURCES}}
_STATE = {{}}   # player -> {{"step": last step seen, "alive": set, "chosen": name|None}}


def _call(fn, obs, cfg):
    try:
        return fn(obs, cfg)
    except TypeError:
        return fn(obs)


def agent(observation, configuration=None):
    obs = observation
    player = obs["player"] if isinstance(obs, dict) else obs.player
    step = obs["step"] if isinstance(obs, dict) else obs.step
    st = _STATE.get(player)
    if st is None or step == 0 or step < st["step"]:
        st = _STATE[player] = {{"step": step, "alive": set(_AGENTS), "chosen": None}}
    st["step"] = step

    if st["chosen"] is not None:
        return _call(_AGENTS[st["chosen"]], obs, configuration)

    # Before the decision every live candidate sees every observation.
    acts = {{}}
    for n in list(st["alive"]):
        try:
            acts[n] = _call(_AGENTS[n], obs, configuration)
        except Exception:
            st["alive"].discard(n)
    ref = acts.get(_DEFAULT)
    if ref is None:                       # default crashed: fall back to anyone alive
        st["chosen"] = next(iter(st["alive"]), _DEFAULT)
        return acts.get(st["chosen"], {{"farmer": ["PASS"], "hands": [], "market": []}})
    key_ref = _json.dumps(ref, sort_keys=True, default=str)
    for n, a in acts.items():             # a candidate that ever disagreed is out for good
        if n != _DEFAULT and _json.dumps(a, sort_keys=True, default=str) != key_ref:
            st["alive"].discard(n)

    if step >= _DECIDE_STEP:
        town = obs["town"] if isinstance(obs, dict) else obs.town
        shops = list((town.get("unlocked_shops") if isinstance(town, dict) else town.unlocked_shops) or [])[:2]
        want = _ROUTE.get("|".join(sorted(shops)), _DEFAULT)
        st["chosen"] = want if want in st["alive"] else _DEFAULT
        return acts[st["chosen"]] if st["chosen"] in acts else ref
    return ref
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cands", required=True, help="comma list; first is the default")
    ap.add_argument("--table", default="", help="json {'A|B': candidate}; empty = always default")
    ap.add_argument("--decide", type=int, default=144)
    ap.add_argument("--force", default="", help="route EVERY world to this candidate (test mode)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cands = [c for c in args.cands.split(",") if c]
    sources, credits = {}, []
    for c in cands:
        p = ROOT / "opponents" / f"{c}.py"
        raw = p.read_bytes()
        sources[c] = base64.b85encode(lzma.compress(raw, preset=9)).decode()
        credits.append(f"#   {c}: {len(raw):,} bytes, embedded unmodified with its own notices")
    route = json.loads(Path(args.table).read_text()) if args.table else {}
    if args.force:
        from itertools import combinations_with_replacement
        shops = ["BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE",
                 "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE"]
        route = {"|".join(sorted(p)): args.force for p in combinations_with_replacement(shops, 2)}

    header = ("# Kaggriculture shop-conditional router.\n"
              "# Routes between public Apache-2.0 agents that share an opening; each candidate\n"
              "# is embedded byte-for-byte and keeps its own upstream licence/attribution notices.\n"
              + "\n".join(credits) + "\n")
    shim = SHIM.format(sources=json.dumps(sources), route=json.dumps(route),
                       default=cands[0], decide=args.decide)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + shim, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes), {len(route)} routed worlds, default {cands[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
