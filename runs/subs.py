import sys; sys.path.insert(0, "scripts"); import kfarm
tok = kfarm.accounts()["ISHRAQ"][1]
r = kfarm.kag("ISHRAQ", tok, "competitions", "submissions", "-c", "kaggriculture")
print(r.stdout[:2500], r.stderr[:300])
