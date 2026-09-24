"""Multi-account Kaggle kernel farm: push jobs, poll, pull results.

Each account gets an isolated KAGGLE_CONFIG_DIR so calls can run in parallel
without fighting over ~/.kaggle/access_token.

  python scripts/kfarm.py accounts                 # verify tokens
  python scripts/kfarm.py probe                    # push N probe kernels/account
  python scripts/kfarm.py status                   # status of all tracked jobs
  python scripts/kfarm.py pull                     # pull outputs of complete jobs
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / "Secrets.env"
CFG_ROOT = Path.home() / ".kaggle" / "accounts"
JOBS = ROOT / "runs" / "jobs.json"


def accounts() -> dict[str, str]:
    """alias -> token, from Secrets.env."""
    users, toks = {}, {}
    for raw in SECRETS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("\"'")
        if k.startswith("KAGGLE_USERNAME_"):
            users[k[16:]] = v
        elif k.startswith("KAGGLE_API_TOKEN_"):
            toks[k[17:]] = v
    return {a: (users.get(a, ""), t) for a, t in toks.items()}


def env_for(alias: str, token: str) -> dict:
    cfg = CFG_ROOT / alias.lower()
    cfg.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["KAGGLE_API_TOKEN"] = token
    env["KAGGLE_CONFIG_DIR"] = str(cfg)
    for k in ("KAGGLE_USERNAME", "KAGGLE_KEY"):
        env.pop(k, None)
    return env


def kag(alias: str, token: str, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    # A timeout is a result, not a crash: when local cores are saturated even the
    # CLI's startup can blow a 60 s budget, and one slow call must not take down
    # a status sweep over 20 kernels.
    try:
        return subprocess.run(
            ["kaggle", *args], capture_output=True, text=True,
            env=env_for(alias, token), check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["kaggle", *args], 124, "", f"timeout after {timeout}s")


def whoami(alias: str, token: str) -> str | None:
    r = kag(alias, token, "config", "view", timeout=180)
    m = re.search(r"username:\s+(\S+)", r.stdout + r.stderr)
    return m.group(1) if m else None


def live_accounts() -> dict[str, tuple[str, str]]:
    """alias -> (username, token) for tokens that actually authenticate.

    KAGRI_ACCOUNTS=A,B restricts to those aliases, so a new job can be pinned to
    accounts that still have free session slots (the cap is 5 per account)."""
    only = {a for a in os.environ.get("KAGRI_ACCOUNTS", "").split(",") if a}
    out = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {a: ex.submit(whoami, a, t) for a, (_u, t) in accounts().items()
                if not only or a in only}
        for a, f in futs.items():
            u = f.result()
            if u:
                out[a] = (u, accounts()[a][1])
    return out


# --------------------------------------------------------------------- jobs

def load_jobs() -> list[dict]:
    if JOBS.exists():
        return json.loads(JOBS.read_text())
    return []


def save_jobs(jobs: list[dict]) -> None:
    JOBS.parent.mkdir(parents=True, exist_ok=True)
    JOBS.write_text(json.dumps(jobs, indent=1))


def push(alias: str, username: str, token: str, slug: str, code: str,
         datasets: list[str] | None = None) -> dict:
    """Push a script kernel. Returns a job record.

    Kaggle derives the real slug from the TITLE, not from metadata `id`, so the
    title IS the slug (>=5 chars) or the ref you poll will not exist."""
    title = slug
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "worker.py").write_text(code, encoding="utf-8")
        (d / "kernel-metadata.json").write_text(json.dumps({
            "id": f"{username}/{slug}",
            "title": title,
            "code_file": "worker.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": False,
            "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": datasets or [],
            "competition_sources": [],
            "kernel_sources": [],
        }), encoding="utf-8")
        r = kag(alias, token, "kernels", "push", "-p", str(d), timeout=600)
    ok = "successfully pushed" in (r.stdout + r.stderr).lower()
    return {
        "alias": alias, "username": username, "slug": slug,
        "ref": f"{username}/{slug}", "pushed": time.time(),
        "ok": ok, "msg": (r.stdout + r.stderr).strip()[:300],
    }


def status(alias: str, token: str, ref: str) -> str:
    r = kag(alias, token, "kernels", "status", ref, timeout=120)
    out = (r.stdout + r.stderr).strip()
    m = re.search(r"KernelWorkerStatus\.([A-Z_]+)", out)
    return m.group(1).lower() if m else out[:120]


def pull(alias: str, token: str, ref: str, dest: Path) -> str:
    dest.mkdir(parents=True, exist_ok=True)
    r = kag(alias, token, "kernels", "output", ref, "-p", str(dest), timeout=600)
    return (r.stdout + r.stderr).strip()[:300]


# --------------------------------------------------------------------- probe

PROBE = r'''
import json, os, time, platform, multiprocessing as mp

def burn(n):
    x = 0
    for i in range(n):
        x = (x * 1103515245 + 12345) & 0xFFFFFFFF
    return x

t0 = time.time(); burn(2_000_000); single = time.time() - t0

cores = os.cpu_count()
t0 = time.time()
with mp.Pool(cores) as p:
    p.map(burn, [2_000_000] * cores)
par = time.time() - t0

try:
    mem = int([l for l in open("/proc/meminfo") if "MemTotal" in l][0].split()[1]) // 1024
except Exception:
    mem = -1

info = {
    "cpu_count": cores,
    "mem_mb": mem,
    "python": platform.python_version(),
    "single_core_s": round(single, 3),
    "parallel_s": round(par, 3),
    "speedup": round(single * cores / par, 2) if par else 0,
    "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
}
print(json.dumps(info, indent=1))
json.dump(info, open("/kaggle/working/probe.json", "w"), indent=1)
'''


# ---------------------------------------------------------------- search jobs

WORKER_TEMPLATE = '''# auto-generated by scripts/kfarm.py -- do not edit
import base64, json, os, sys, zlib

BUNDLE = {bundle!r}
ROOT = "/kaggle/working/src"


def _unpack():
    """Runs at import in the parent AND in every spawned child, so the child can
    re-import `search` and unpickle the worker function."""
    files = json.loads(zlib.decompress(base64.b64decode(BUNDLE)).decode())
    for name, blob in files.items():
        p = os.path.join(ROOT, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.exists(p):
            open(p, "w", encoding="utf-8").write(blob)
    for sub in ("opt", "engine"):
        d = os.path.join(ROOT, sub)
        if d not in sys.path:
            sys.path.insert(0, d)


_unpack()

if __name__ == "__main__":
    sys.argv = ["{entry}.py"] + {argv!r}
    import {entry} as _entry
    raise SystemExit(_entry.main())
'''


# Panel members shipped inside the worker. Each one roughly doubles the bundle,
# and a Kaggle script kernel starts failing well before 2 MB -- two different
# lineages (pipe-7 tape, v50 yarn build) is the useful/size sweet spot.
WORKER_PANEL = ["pipe-7-wheat-microstructure", "v50-early-yarn-commit"]


def build_worker(argv: list[str], seed_pool: list | None = None,
                 entry: str = "search", panel: bool = True) -> str:
    """One self-contained .py: engine, policy, searcher and panel inlined.

    No pip install, no dataset attachment, no internet -- a Kaggle kernel that
    needs none of those starts in seconds and cannot fail on a missing input."""
    import base64
    import zlib
    files = {
        "engine/kaggriculture_ref.py": ROOT / "engine" / "kaggriculture_ref.py",
        "engine/kaggriculture.json": ROOT / "engine" / "kaggriculture.json",
        "engine/fastsim.py": ROOT / "engine" / "fastsim.py",
        "opt/policy.py": ROOT / "opt" / "policy.py",
        "opt/search.py": ROOT / "opt" / "search.py",
        "opt/worldeval.py": ROOT / "opt" / "worldeval.py",
        "opt/opponents.py": ROOT / "opt" / "opponents.py",
        "opt/shed_guard.py": ROOT / "opt" / "shed_guard.py",
        "opt/sale_advance.py": ROOT / "opt" / "sale_advance.py",
        "opt/idle_work.py": ROOT / "opt" / "idle_work.py",
    }
    for name in (WORKER_PANEL if panel else []):
        files[f"opponents/{name}.py"] = ROOT / "opponents" / f"{name}.py"
    bundle = {k: v.read_text(encoding="utf-8", errors="replace") for k, v in files.items()}
    if seed_pool:
        bundle["opt/seed.json"] = json.dumps({"elites": seed_pool})
    blob = base64.b64encode(zlib.compress(json.dumps(bundle).encode(), 9)).decode()
    return WORKER_TEMPLATE.format(bundle=blob, argv=argv, entry=entry)


def cmd_run(minutes: int = 120, per_account: int = 5, mode: str = "cash",
            opp: str = "starter", pop: int = 48, seeds: int = 5, resume: str = "") -> int:
    """Launch one search island per available session across every account.

    `resume` is a local checkpoint (e.g. runs/best.json) whose elites get bundled
    into every worker, so a round starts where the last one stopped."""
    live = live_accounts()
    seed_pool = None
    if resume and Path(resume).exists():
        d = json.loads(Path(resume).read_text())
        seed_pool = d.get("elites") or [g["genome"] for g in d.get("pool", []) if g.get("genome")]
        print(f"seeding every island with {len(seed_pool or [])} genomes from {resume}")
    tasks = []
    idx = 0
    for a, (u, t) in sorted(live.items()):
        for i in range(per_account):
            argv = [
                "--minutes", str(minutes), "--procs", "4",
                "--pop", str(pop), "--elite", "8", "--seeds", str(seeds),
                "--opp", opp, "--mode", mode,
                # Each island explores a different sigma and a different seed
                # block, so 20 kernels are 20 searches, not 20 copies of one.
                "--sigma", ["0.10", "0.18", "0.28", "0.40", "0.15"][i % 5],
                "--seed-base", str(1000 + idx * 997),
                "--rng", str(7919 + idx),
                "--island", f"{a.lower()}-{i}",
                "--out", "/kaggle/working/island.json",
            ]
            if seed_pool:
                argv += ["--resume", "/kaggle/working/src/opt/seed.json"]
            tasks.append((a, u, t, f"kagri-isl-{a.lower()}-{i}",
                          build_worker(argv, seed_pool)))
            idx += 1
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda x: push(x[0], x[1], x[2], x[3], x[4]), tasks))
    for r in res:
        r["kind"] = "island"
        print(("ok   " if r["ok"] else "FAIL ") + r["ref"] + ("" if r["ok"] else "  " + r["msg"][:110]))
    save_jobs([j for j in load_jobs() if j.get("kind") != "island"] + res)
    print(f"\n{sum(1 for r in res if r['ok'])}/{len(res)} islands launched, {minutes} min each")
    return 0


def cmd_harvest() -> int:
    """Pull every finished island and report the best genomes found."""
    live = live_accounts()
    best = []
    for j in load_jobs():
        if j.get("kind") != "island" or j["alias"] not in live:
            continue
        tok = live[j["alias"]][1]
        dest = ROOT / "runs" / "islands" / j["slug"]
        pull(j["alias"], tok, j["ref"], dest)
        f = dest / "island.json"
        if not f.exists():
            print(f"{j['ref']:44s} no output yet")
            continue
        d = json.loads(f.read_text())
        best.append((d.get("best_fitness", 0), d.get("gen", 0), j["slug"], d.get("best")))
        print(f"{j['slug']:30s} gen={d.get('gen',0):4d}  best={d.get('best_fitness',0):14,.0f}")
    if best:
        best.sort(key=lambda b: -b[0])
        top = ROOT / "runs" / "best.json"
        top.write_text(json.dumps({
            "best_fitness": best[0][0], "from": best[0][2], "best": best[0][3],
            "pool": [{"fitness": b[0], "island": b[2], "genome": b[3]} for b in best[:20]],
        }, indent=1))
        print(f"\nbest overall {best[0][0]:,.0f} from {best[0][2]} -> {top}")
    return 0


# ------------------------------------------------------------ world evaluation

FAMILY_H = "c-tetsutani-0921,c-wheat-seller,c-one-more-wheat"
PANEL_12 = ("c-koshinm-0921,c-koshinm-0920,c-tetsutani-0921,c-wheat-seller,c-one-more-wheat,"
            "c-v53,v50-early-yarn-commit,shop-router-reactive-v7,v54-idle-workers,"
            "c-anhad-metav4,c-wonderful,c-2950")


def cmd_worldeval(minutes: int = 180, per_account: int = 5, seed_base: int = 200000,
                  cands: str = FAMILY_H, opps: str = PANEL_12, tag: str = "we") -> int:
    """Shard seeds over every free session. Each kernel mounts its own account's
    private kagri-panel dataset and streams results; the budget ends it cleanly."""
    live = live_accounts()
    tasks, k = [], 0
    for a, (u, t) in sorted(live.items()):
        for i in range(per_account):
            lo = seed_base + k * 1000
            argv = ["--cands", cands, "--opps", opps, "--seed-lo", str(lo),
                    "--seed-hi", str(lo + 1000), "--procs", "4",
                    "--out", "/kaggle/working/we.jsonl", "--minutes", str(minutes)]
            code = build_worker(argv, entry="worldeval", panel=False)
            tasks.append((a, u, t, f"kagri-{tag}-{a.lower()}-{i}", code, [f"{u}/kagri-panel"]))
            k += 1
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda x: push(x[0], x[1], x[2], x[3], x[4], x[5]), tasks))
    for r in res:
        r["kind"] = tag
        print(("ok   " if r["ok"] else "FAIL ") + r["ref"] + ("" if r["ok"] else "  " + r["msg"][:140]))
    save_jobs([j for j in load_jobs() if j.get("kind") != tag] + res)
    print(f"\n{sum(r['ok'] for r in res)}/{len(res)} shards launched, {minutes} min each")
    return 0


def cmd_harvest_we(tag: str = "we") -> int:
    """Pull finished world-eval shards and concatenate to runs/<tag>_all.jsonl."""
    live = live_accounts()
    rows = 0
    out = ROOT / "runs" / f"{tag}_all.jsonl"
    with out.open("w") as f:
        for j in load_jobs():
            if j.get("kind") != tag or j["alias"] not in live:
                continue
            tok = live[j["alias"]][1]
            st = status(j["alias"], tok, j["ref"])
            dest = ROOT / "runs" / tag / j["slug"]
            if st == "complete":
                pull(j["alias"], tok, j["ref"], dest)
            src = dest / "we.jsonl"
            n = 0
            if src.exists():
                for line in src.read_text().splitlines():
                    if line.strip():
                        f.write(line + "\n")
                        n += 1
            rows += n
            print(f"{j['ref']:44s} {st:10s} {n:6d} games")
    print(f"\n{rows} games -> {out}")
    return 0


def cmd_accounts() -> int:
    live = live_accounts()
    allacc = accounts()
    for a, (u, _t) in sorted(allacc.items()):
        print(f"{'OK ' if a in live else 'DEAD'} {a:12s} {u}")
    print(f"\n{len(live)}/{len(allacc)} usable")
    return 0


def cmd_probe(per_account: int = 2) -> int:
    live = live_accounts()
    jobs = load_jobs()
    tasks = []
    for a, (u, t) in sorted(live.items()):
        for i in range(per_account):
            tasks.append((a, u, t, f"kagri-probe-{a.lower()}-{i}"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda x: push(x[0], x[1], x[2], x[3], PROBE), tasks))
    for r in res:
        print(("ok   " if r["ok"] else "FAIL ") + r["ref"] + ("" if r["ok"] else "  " + r["msg"]))
        r["kind"] = "probe"
    save_jobs(jobs + res)
    return 0


def cmd_status() -> int:
    live = live_accounts()
    for j in load_jobs():
        if j["alias"] not in live:
            continue
        tok = live[j["alias"]][1]
        print(f"{j['ref']:48s} {status(j['alias'], tok, j['ref'])}")
    return 0


def cmd_pull() -> int:
    live = live_accounts()
    for j in load_jobs():
        if j["alias"] not in live:
            continue
        tok = live[j["alias"]][1]
        dest = ROOT / "runs" / "out" / j["slug"] / j["alias"]
        print(j["ref"], pull(j["alias"], tok, j["ref"], dest))
        p = dest / "probe.json"
        if p.exists():
            print("   ", p.read_text().replace("\n", " "))
    return 0


if __name__ == "__main__":
    cmds = {"accounts": cmd_accounts, "probe": cmd_probe, "status": cmd_status,
            "pull": cmd_pull, "run": cmd_run, "harvest": cmd_harvest,
            "worldeval": cmd_worldeval, "harvest_we": cmd_harvest_we}
    name = sys.argv[1] if len(sys.argv) > 1 else "accounts"
    if name not in cmds:
        print(__doc__)
        raise SystemExit(1)
    args = [int(a) if a.isdigit() else a for a in sys.argv[2:]]
    raise SystemExit(cmds[name](*args))
