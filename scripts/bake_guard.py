"""Bake the external shed-overflow guard (opt/shed_guard.py) permanently onto a
base agent, for submission. The base agent's source is embedded completely
unmodified (all its own upstream notices retained); our guard is appended as
plain code at the end, and reassigns `agent` to the wrapped version so it is
the last callable in the file (matches how every loader in this lineage picks
the entry point).

    python scripts/bake_guard.py c-koshinm-0921 10 --out runs/sub_koshinm_guarded/main.py
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FOOTER_TMPL = '''

# ---- external shed-overflow guard (added {when}) ----------------------------
# Wraps the agent above WITHOUT modifying it: after its own action, if
# projected end-of-day shed+carried inventory would exceed shedCapacity, sells
# the highest-price excess stock (skipping anything already being sold) to
# avoid the silent end-of-day discard. Confirmed by a paired one-parameter
# sweep of the trigger margin against an 8-agent panel across two independent
# seed ranges (see opt/shed_guard.py, PLAN.md): margin={margin} was the winner.
# On any error it falls back to the base agent's own action unchanged.
_GUARD_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def _guard_get(obs, key, default=None):
    return obs[key] if isinstance(obs, dict) else getattr(obs, key, default)


def _guard_apply(obs, action, margin={margin}, min_price=2):
    if not isinstance(action, dict):
        return action
    player = _guard_get(obs, "player")
    farms = _guard_get(obs, "farms")
    private = _guard_get(obs, "private")
    market = _guard_get(obs, "market")
    if player is None or not farms or not private or not market:
        return action
    farm = farms[player]
    shed = dict(private.get("shed", {{}}) if isinstance(private, dict) else private["shed"])
    orders = list(action.get("market") or [])
    if len(orders) >= 10:
        return action
    already_selling = {{o[1] for o in orders if isinstance(o, list) and len(o) >= 2 and o[0] == "SELL"}}
    inventories = private.get("inventories", []) if isinstance(private, dict) else private["inventories"]
    carried = sum(max(0, int(v)) for inv in inventories for v in inv.values())
    units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
    for i, cmd in enumerate(units):
        if not cmd:
            continue
        op = cmd[0]
        if op == "HARVEST":
            pos = farm["farmer"] if i == 0 else (farm["hands"][i - 1] if i - 1 < len(farm["hands"]) else None)
            if pos:
                tile = farm["tiles"][pos[1]][pos[0]]
                if isinstance(tile, dict):
                    carried += max(0, int(tile.get("yield_units", 0)))
        elif op == "COLLECT_FERTILIZER":
            carried += 1
        elif op == "DROP":
            carried = max(0, carried - sum(max(0, int(v)) for v in (inventories[i] if i < len(inventories) else {{}}).values()))
    total = sum(max(0, int(v)) for v in shed.values()) + carried
    excess = total - 100 + margin
    if excess <= 0:
        return action
    prices = market.get("prices", {{}})
    cands = sorted(
        ((int(prices.get(it, 0)), it, int(shed.get(it, 0))) for it in _GUARD_PRODUCTS
         if it not in already_selling and int(shed.get(it, 0)) > 0 and int(prices.get(it, 0)) >= min_price),
        reverse=True,
    )
    extra = []
    need = excess
    for price, item, avail in cands:
        if need <= 0 or len(orders) + len(extra) >= 10:
            break
        qty = min(need, avail)
        if qty > 0:
            extra.append(["SELL", item, qty])
            need -= qty
    if not extra:
        return action
    return dict(action, market=orders + extra)


_GUARD_BASE_AGENT = agent


def agent(observation, configuration=None):
    try:
        import inspect
        _takes_cfg = len(inspect.signature(_GUARD_BASE_AGENT).parameters) >= 2
    except (TypeError, ValueError):
        _takes_cfg = False
    action = _GUARD_BASE_AGENT(observation, configuration) if _takes_cfg else _GUARD_BASE_AGENT(observation)
    try:
        return _guard_apply(observation, action)
    except Exception:
        return action
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("margin", type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    base_path = Path(args.base)
    if not (base_path.suffix == ".py" and base_path.exists()):
        base_path = ROOT / "opponents" / f"{args.base}.py"
    src = base_path.read_bytes()
    footer = FOOTER_TMPL.format(when=time.strftime("%Y-%m-%d"), margin=args.margin).encode("utf-8")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(src + footer)
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
