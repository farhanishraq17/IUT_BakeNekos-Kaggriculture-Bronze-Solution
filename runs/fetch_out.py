import sys, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, "scripts"); import kfarm
tok = kfarm.accounts()["ISHRAQ"][1]
env = kfarm.env_for("ISHRAQ", tok); env["PYTHONIOENCODING"] = "utf-8"
def get(ref):
    d = Path("runs/newout") / ref.split("/")[1]; d.mkdir(exist_ok=True, parents=True)
    r = subprocess.run(["kaggle", "kernels", "output", ref, "-p", str(d)], capture_output=True, text=True, encoding="utf-8", env=env, timeout=600)
    files = [p for p in d.rglob("*") if p.is_file()]
    return f"{ref}: {[ (p.name, p.stat().st_size) for p in files][:8]} {r.stderr[-150:]}"
with ThreadPoolExecutor(6) as ex:
    for line in ex.map(get, sys.argv[1:]): print(line)
