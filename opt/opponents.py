"""The evaluation panel: the public leaderboard agents, loaded from opponents/.

These are Apache-2.0 sources extracted from public competition notebooks (see
scripts/extract_agents.py). They are the benchmark, never edited, and never
shipped inside our submission.

Loaded lazily and cached per process -- some are 1 MB of Python and importing
all of them in every pool worker would cost more than the games do.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parents[1]
# On a Kaggle worker the panel arrives as a mounted dataset, not a repo folder.
DIR = Path(os.environ.get("KAGRI_PANEL_DIR", ROOT / "opponents"))
sys.path.insert(0, str(ROOT / "engine"))

import fastsim  # noqa: E402

_cache: dict[str, object] = {}

# Ordered weakest -> strongest as far as we know. `starter`/`pass` stay in for
# bootstrapping a genome that cannot yet finish a season alive.
BUILTIN = {"pass": lambda: fastsim.REF.pass_agent, "starter": lambda: fastsim.REF.starter_agent}


def available() -> list[str]:
    files = [p.stem for p in DIR.glob("*.py") if p.stem != "__init__"]
    dirs = [p.name for p in DIR.iterdir() if p.is_dir() and (p / "main.py").exists()]
    return sorted(BUILTIN) + sorted(files + dirs)


def _variant(name: str):
    """'base@KNOB=VALUE[@KNOB2=V2]' -> the base agent with those top-level constants
    rewritten. Built at load time, so a farm worker needs only the base file from
    the panel dataset, not a 1 MB upload per variant. Each knob must occur exactly
    once as `KNOB = ...` at line start, or the build refuses."""
    import re
    import tempfile
    base, *subs = name.split("@")
    path = DIR / f"{base}.py"
    src = path.read_text(encoding="utf-8")
    for s in subs:
        knob, value = s.split("=", 1)
        pat = re.compile(rf"^{re.escape(knob)}[ \t]*=[ \t]*[^\n]*$", re.M)
        hits = pat.findall(src)
        if len(hits) != 1:
            raise KeyError(f"{knob!r} matched {len(hits)} lines in {base}; need exactly 1")
        src = pat.sub(f"{knob} = {value}", src, count=1)
    out = Path(tempfile.gettempdir()) / f"kagri_var_{abs(hash(name))}.py"
    out.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"_v_{abs(hash(name))}", out)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def get(name: str):
    if name in _cache:
        return _cache[name]
    if name.startswith("guard:"):
        # "guard:BASE:MARGIN" -> BASE wrapped in the external shed-overflow guard
        # (see shed_guard.py). Lets us test the guard on agents whose internals
        # we cannot safely edit (koshinm: see CLAUDE.md).
        # optional 4th field: comma list of h<hour_min>, w<wheat_keep>, s<ITEM> (skip)
        parts = name.split(":")
        base_name, margin = parts[1], int(parts[2])
        kw = {"hour_min": 0, "wheat_keep": 0, "skip": ()}
        # options joined with "+" (commas would break comma-separated CLI lists)
        for o in (parts[3].replace(",", "+").split("+") if len(parts) > 3 and parts[3] else []):
            if o[0] == "h":
                kw["hour_min"] = int(o[1:])
            elif o[0] == "w":
                kw["wheat_keep"] = int(o[1:])
            elif o[0] == "s":
                kw["skip"] = tuple(kw["skip"]) + (o[1:],)
            elif o[0] == "c":
                kw["seed_cutoff"] = int(o[1:])
            elif o[0] == "f":
                kw["fert_cutoff"] = int(o[1:])
            elif o[0] == "p":
                kw["min_price"] = int(o[1:])
            elif o[0] == "L":
                kw["cheap_first"] = True
            elif o[0] == "e":
                kw["endgame_step"] = int(o[1:])
            elif o[0] == "E":
                kw["late_step"] = int(o[1:])
            elif o[0] == "M":
                kw["late_margin"] = int(o[1:])
            elif o == "T":
                kw["topup"] = True
            elif o == "t":
                kw["topup_end"] = True
        import shed_guard
        _cache[name] = shed_guard.wrap(get(base_name), margin=margin, **kw)
        return _cache[name]
    if name.startswith("trade:"):
        # "trade:BASE[:opts]" -> BASE + the wheat-speculation layer (trader.py).
        # opts joined with "+": b<buy_below>, u<buy_until>, s<sell_after>,
        # m<max_hold>, a<sell_above>. The base may itself be a guard: name whose
        # own opts use the same letters ("sMILK"), so a trailing field counts as
        # trader opts only if EVERY token is <letter><digits>.
        import re as _re
        parts = name[len("trade:"):].split(":")
        kw = {}
        if len(parts) > 1 and parts[-1] and all(
                _re.fullmatch(r"[busma]\d+", t) for t in parts[-1].replace(",", "+").split("+")):
            for o in parts.pop().replace(",", "+").split("+"):
                kw[{"b": "buy_below", "u": "buy_until", "s": "sell_after",
                    "m": "max_hold", "a": "sell_above"}[o[0]]] = int(o[1:])
        base_name = ":".join(parts)
        import trader
        _cache[name] = trader.wrap(get(base_name), **kw)
        return _cache[name]
    if name.startswith("idle:"):
        # "idle:BASE[:opts]" -> BASE + the idle-unit layer (see idle_work.py).
        # opts joined with "+": c(are), f(ertilizer), w(ater); default care only.
        parts = name[len("idle:"):].split(":")
        opts = parts.pop() if len(parts) > 1 and set(parts[-1]) <= set("cfw+,") else ""
        base_name = ":".join(parts)
        o = opts.replace(",", "+").split("+") if opts else ["c"]
        import idle_work
        _cache[name] = idle_work.wrap(get(base_name), care="c" in o, fert="f" in o, water="w" in o)
        return _cache[name]
    if name.startswith("adv:"):
        # "adv:BASE:LEAD:MINEVENTS[:opts]" -> BASE + the sale-advance layer
        # (see sale_advance.py). opts joined with "+": u<min_units>, p<min_price>,
        # s<start_step>.
        # Parsed from the RIGHT: the base may itself be a "guard:BASE:MARGIN"
        # name, so it can contain colons. Trailing fields are lead, min_events
        # and an optional opts field (the only non-numeric one).
        parts = name[len("adv:"):].split(":")
        opts = parts.pop() if parts and not parts[-1].lstrip("-").isdigit() else ""
        min_events = int(parts.pop())
        lead = int(parts.pop())
        base_name = ":".join(parts)
        kw = {"lead": lead, "min_events": min_events}
        for o in (opts.replace(",", "+").split("+") if opts else []):
            if o[0] == "u":
                kw["min_units"] = int(o[1:])
            elif o[0] == "p":
                kw["min_price"] = int(o[1:])
            elif o[0] == "s":
                kw["start_step"] = int(o[1:])
        import sale_advance
        _cache[name] = sale_advance.wrap(get(base_name), **kw)
        return _cache[name]
    if "@" in name:
        _cache[name] = _variant(name)
        return _cache[name]
    if name in BUILTIN:
        fn = BUILTIN[name]()
    else:
        path = DIR / f"{name}.py"
        if not path.exists() and (DIR / name / "main.py").exists():
            # Multi-file agent (a submission tarball): its siblings must be importable.
            path = DIR / name / "main.py"
            if str(path.parent) not in sys.path:
                sys.path.insert(0, str(path.parent))
        if not path.exists():
            raise KeyError(f"no opponent {name!r}; have {available()}")
        spec = importlib.util.spec_from_file_location(f"_opp_{name.replace('-', '_')}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = mod.agent
    _cache[name] = fn
    return fn


def get_path(path: str):
    """Load an agent from an arbitrary file (generated variants). Cached per process."""
    key = "path:" + path
    if key not in _cache:
        spec = importlib.util.spec_from_file_location(f"_var_{abs(hash(path))}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache[key] = mod.agent
    return _cache[key]


# The panel used for fitness. Kept small on purpose: each of these costs ~1 s per
# game, so every extra member is a direct tax on generations per hour.
PANEL = ["pipe-7-wheat-microstructure", "v50-early-yarn-commit", "shop-router-reactive-v7"]


if __name__ == "__main__":
    import time
    for name in available():
        try:
            fn = get(name)
        except Exception as e:  # noqa: BLE001
            print(f"{name:36s} LOAD FAILED: {type(e).__name__}: {e}")
            continue
        t = time.time()
        try:
            m = fastsim.run(fn, fastsim.REF.starter_agent, seed=11)
            dt = time.time() - t
            print(f"{name:36s} ${m[0]:11,.0f} vs starter ${m[1]:8,.0f}  "
                  f"{dt*1000:6.0f} ms  errors={fastsim.run.errors}")
        except Exception as e:  # noqa: BLE001
            print(f"{name:36s} RUN FAILED: {type(e).__name__}: {e}")
