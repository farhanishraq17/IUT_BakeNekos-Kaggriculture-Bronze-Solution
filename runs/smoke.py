import sys, time
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents
for n in sys.argv[1:]:
    t = time.time()
    try:
        fn = opponents.get(n)
        m = fastsim.run(fn, fastsim.REF.starter_agent, seed=11)
        print(f"{n:26s} ${m[0]:>10,.0f} vs starter ${m[1]:>7,.0f}  {(time.time()-t)*1000:6.0f} ms  err={fastsim.run.errors}")
    except Exception as e:
        print(f"{n:26s} FAILED {type(e).__name__}: {e}")
