import sys, subprocess, json, glob, os, re
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "scripts"); import kfarm
tok = kfarm.accounts()["ISHRAQ"][1]
env = kfarm.env_for("ISHRAQ", tok); env["PYTHONIOENCODING"]="utf-8"
def eps(sub):
    r = subprocess.run(["kaggle","competitions","episodes",sub,"--csv"],capture_output=True,text=True,encoding="utf-8",env=env)
    return [l.split(",")[0] for l in r.stdout.splitlines() if "COMPLETED" in l][:15]
def get(eid):
    d=f"runs/livediag/{eid}"; os.makedirs(d,exist_ok=True)
    if not glob.glob(d+"/*"):
        subprocess.run(["kaggle","competitions","replay",eid,"-p",d],capture_output=True,env=env,timeout=600)
    return eid
for sub in sys.argv[1:]:
    ids=eps(sub)
    with ThreadPoolExecutor(8) as ex: list(ex.map(get, ids))
    json.dump(ids, open(f"runs/livediag/{sub}.ids","w"))
    print(sub, len(ids))
