# Kaggriculture — progress and handoff

**Last updated: 2026-09-25.** Read `CLAUDE.md` first (engine facts, hard constraints, working rules),
then this file. `PLAN.md` is the dated experiment log — this file is the *current* state.

Competition ends **2026-09-30**. 5 submissions/day, only the **latest 2** count for the final
Bradley-Terry leaderboard. Prize: top 10.

**Standing instruction: do not submit without the user's explicit approval.** Propose, show the
numbers, wait for a yes.

---

## 1. Where we stand

Submit **only** from ISHRAQ (`farhanishraqq`). Submitting the same agent from teammate accounts is
multi-account abuse.

| Sub ID | Date | Agent | Live rating |
|---|---|---|---|
| **56508972** | 09-24 | **Frontier-0923 + our shed guard (margin 14)** | **2452.5** at 5 h, still climbing |
| 56502436 | 09-23 | haodou092 Harvest Ledger (0922 build) | 2051.3 |
| 56502435 | 09-23 | prvsiyan Frontier (0922 build) | 2383.0 |
| 56497677 | 09-23 | tetsutani-0921 resubmitted, byte-identical to the 2583.1 file | 2193.6 |
| 56470642 | 09-22 | dmitriigluzdov Herd-Safe | 2478.5 |
| 56470640 | 09-22 | tetsutani-0922 | 2212.9 |
| 56457171 | 09-22 | tetsutani tuned + guard (ours) | 2318.3 |
| 56455306 | 09-22 | koshinm + guard (ours) | 2107.8 |
| 56452572 | 09-22 | tetsutani + 2-knob tuning (ours) | 2429.3 |
| 56442778 / 56442774 | 09-21 | koshinm / tetsutani unmodified | 2459.6 / **2583.1** |
| 56406154 | 09-20 | public fork-2801 | 1934.8 |
| 56406056 / 56405251 | 09-20 | our own from-scratch policies | 495 / 434 |

Highest number ever seen: 2583.1 on 09-21. **That number is not a target — see section 2.**
Target: 3000.

---

## 2. Ratings drift down over time — never compare across days

The same file, resubmitted two days later, scored **2583.1 → 2192.5**. Byte-identical
(`opponents/c-tetsutani-0921.py`, sha `9c0a8921`), same account.

destbreso's `ladder_forecast.json` (in `data/bench/`, from `destbreso/kaggriculture-benchmark-matchups`)
shows the same effect independently: a fixed submission's median rating decays from 2087 at episode 146
to 1738 by episode 266 as the field strengthens.

Consequences:
- A rating is only meaningful against other agents rated **in the same window**.
- Our earlier conclusion that "our modifications rate lower live than their parents" was **partly an
  artifact of this drift** — the modified versions were rated in a stronger field. It is no longer
  treated as established.
- 3000 today is a far stronger agent than 3000 would have been a week ago.

A new submission starts at 600 and needs roughly a day to converge. Judge two agents by comparing
them at the *same age*, not by their current numbers.

---

## 3. Methodology trap that cost us a whole experiment

**Never put a candidate's own base into the opponent list.** Farm job `g3` measured the guard on
Frontier with Frontier-0923 itself among the opponents, so the guarded version was credited for
beating its own unguarded mirror: it reported **+4.34pp (z=9.41)**. The same comparison with a
mirror-free opponent set gives **+2.48pp**. The inflated `g3` numbers for Harvest Ledger (+22.6pp)
and dmitrii-2700 (+28.9pp) have the same defect and must not be quoted.

Rule: the opponent field must be fixed, and disjoint from the candidate list.

Second trap, already known but re-confirmed: small paired samples swing sign. The same local guard
test read −2.42pp (z=−1.90) at n=496 and +1.21pp (z=1.21) at n=912. Do not act below a few thousand
paired cells.

---

## 4. What has been tried

### Confirmed, and shipped

| Finding | Evidence | Status |
|---|---|---|
| **Shed-overflow guard, margin 14, on Frontier-0923** | **+2.48pp, z=12.95, 136,811 paired games, mirror-free, 3 independent seed ranges** | live as 56508972 |
| Guard margins: 14 best, then 18 (+2.40), 10 (+2.19), 22 (+2.00) | same pooled test | 14 shipped |
| Fertilizer purchase cutoff at step 684 | +1.03pp z=17.8 on the old tetsutani base (87k games); **no added effect on Frontier** (identical to margin 14 alone) | not needed on current base |

### Confirmed on older bases, value on current bases unproven

- Guard on koshinm (+2.86pp z=8.12), on tetsutani-tuned (+1.73pp z=3.66), and +1 to +26pp across
  seven 09-21-era public agents. Those bases are now 20–60 points behind the field.
- tetsutani knobs `_SR_MARGIN` 8→12, `_Y_MARGIN` −6→−12 (+1.95pp z=7.02, 211k games).

### Dead ends — do not retry without a new hypothesis

- **Our own policy from scratch** (`opt/policy.py`, `opt/search.py`): plateaued ~6× behind public
  agents, live 434–495. All 20 farm islands hit the same ceiling, so it is expressiveness, not budget.
- Round-2 tetsutani knob sweep (12 constants, 123k games): nothing significant; several constants
  confirmed already optimal in both directions.
- v50 opening tweaks: every change catastrophic; the tape is funded to the exact coin.
- Routing within an agent family: per-game oracle equals the default.
- Cloning top-10 replays: they are reactive from turn 0.
- `opt/tapeeval.py` vs top-10 tapes: uninformative.
- Guard variants: hour gating (−6 to −20pp), wheat reserve (−2 to −3pp), skipping WHEAT or
  FERTILIZER (−2pp), margins 6/8 (−16 to −19pp).
- Time-based seed-purchase cutoffs (c636–c666): −7 to −55pp. Note the Herd-Safe authors do this
  *need-based* (limit late seeds to remaining planting work) and report it as a win — the idea is
  fine, our blunt implementation was not.
- Shop steering ("God's mode"): directed control only ~10–18%, score impact unmeasured. Parked.

---

## 5. The public meta, as of 2026-09-24

Features that distinguish the current top builds, from the Code-tab survey:

| Feature | Source | Our status |
|---|---|---|
| Opponent-sale forecast: predict rival SELLs 1–4 turns ahead and sell first, gated on ≥3 matching historical events and ≥70% precision over 240 turns | Herd-Safe v3 "forecast4" (arsgorynich); also in `c-shepherds-0924` | not ported; `g5` tests whether guarding a forecast-carrying base beats ours |
| Avoid fertilizer that cannot improve the planned harvest | Herd-Safe (dmitriigluzdov) | independently found by us (f684) |
| Late seed purchases limited to remaining planting work | Herd-Safe | our time-based version failed |
| Reduced opening wheat round-trip, keeping 5 wheat + planting seed | Herd-Safe | untested |
| Bounded 7-turn terminal delivery planner | Herd-Safe | our bases already liquidate to $0 |
| Reordering contiguous SELL blocks after the other market layers | Frontier (prvsiyan) on haideptry's Master Hybrid 2965 | inside our current base |
| Shed-overflow guard before the 100-item cap | **ours** | shipped |

**Agent ranking — farm `rr2`, 113,378 games, 0 errors** (local run on separate seeds agreed,
13,873 games, same order at the top):

| Agent | Farm | Local |
|---|---|---|
| **c-frontier-0923** | **89.8%** | **80.8%** |
| c-frontier-0922 | 74.5% | 65.0% |
| c-v15stack | 67.8% | 66.6% |
| c-shepherds-ledger | 67.7% | 70.6% |
| c-pop-robust | 67.7% | 66.4% |
| c-late-v16 | 67.1% | 64.8% |
| c-herdsafe-v3 | 66.3% | 72.7% |
| c-harvest-ledger-0923 | 43.7% | 41.5% |
| c-herdsafe-ca25 | 43.5% | 48.8% |
| c-dmitrii-2700 | 43.0% | 47.4% |
| c-tetsutani-0921 | 27.8% | 27.2% |
| c-thomas-2944 | 23.1% | 31.1% |

Offline ranking and live rating correlate only loosely (dmitrii-2700 is 43% offline and was our
best live agent for two days). Treat offline as a filter, live as the verdict.

Agents live in `opponents/` as plain `.py`. The `c-` prefix means the file came from
`kaggle kernels output`, i.e. the exact file that author submitted — always prefer that over
notebook extraction.

---

## 6. Compute

**7 Kaggle accounts × 5 concurrent CPU sessions = 35 kernels**, each 4 vCPU / 12 h max.
Tokens in `Secrets.env`: ISHRAQ, DIDHITI, TASHIN, SALAM, Eshad, Mashrafi, Samin. All authenticate.
Plus local: 20 logical cores, though these 1 MB agents run ~700 ms/game, so expect a few games/s,
not the 73/s the old lightweight policies managed.

```bash
python scripts/panel_dataset.py                       # after adding agents to opponents/
python scripts/kfarm.py worldeval <min> 5 <seed_base> "<cands>" "<opps>" <tag>
KAGRI_ACCOUNTS=Mashrafi,Samin python scripts/kfarm.py worldeval ...   # pin to free accounts
python scripts/kfarm.py status
python scripts/kfarm.py harvest_we <tag>              # -> runs/<tag>_all.jsonl
python opt/paired.py "<base cand>" runs/<tag>_all.jsonl [more.jsonl] --only SUBSTR
```

`KAGRI_ACCOUNTS=A,B` (added 09-24) restricts a launch to those accounts, so a second job can use
accounts that still have free slots — the 5-session cap is per account and pushing a 6th errors.

A 35-shard × 120 min run yields roughly 100–130k games. Kernel output is only retrievable after the
kernel completes; harvesting 35 shards takes several minutes.

---

## 7. Tooling

```
engine/fastsim.py          fast engine, parity-verified
engine/test_parity.py      THE GATE — run after any engine/fastsim edit
opt/opponents.py           load any agent by name; runtime variants (below)
opt/worldeval.py           paired evaluation, --cands/--opps/--seed-lo/--seed-hi/--minutes/--out
opt/paired.py              paired deltas + z per candidate from jsonl
opt/shed_guard.py          external pre-cap selling wrapper, no agent internals needed
opt/sweep_eval.py          one-knob paired sweeps
opt/replays.py             verify/match live replays
scripts/kfarm.py           the farm
scripts/panel_dataset.py   upload opponents/ as the private kagri-panel dataset
scripts/fetch_notebooks.py pull notebook sources (for reading the authors' method notes)
scripts/extract_agents.py  AST-based extraction from notebooks (writes BYTES — never text)
scripts/bake_guard.py      permanently append the guard to an agent
scripts/bake_variant.py    permanently substitute a knob value
scripts/build_submission.py  validate(path) = official kaggle_environments gate
runs/fetch_out.py          download kernel OUTPUTS (the exact submitted main.py / tarball)
runs/smoke.py              load + one game vs starter, for any new agent
runs/verify_bake.py        baked file must equal the evaluated runtime variant
runs/wait_tags.py          poll farm tags to completion, then harvest each
runs/livediag.py/_an.py    download and analyse our own live replays
```

**Runtime agent naming** (no file edits needed to evaluate a variant):
- `name@KNOB=VALUE[@K2=V2]` — rewrite a top-level constant (must match exactly one line)
- `guard:BASE:MARGIN[:opts]` — wrap in the shed guard; options joined with `+`:
  `h<hour_min>`, `w<wheat_keep>`, `s<ITEM>` (skip), `c<seed_cutoff>`, `f<fert_cutoff>`

---

## 8. Submission procedure

```python
kfarm.kag("ISHRAQ", token, "competitions", "submit", "-c", "kaggriculture", "-f", path, "-m", msg)
```
Either a bare `main.py` or the author's `submission.tar.gz`; prefer the tarball when it ships
`LICENSE.txt` / `NOTICE.txt`.

**Non-negotiable:** public agents are Apache-2.0. Keep every upstream notice, name the authors in the
description, never strip authorship.

Gates for anything **we modified**:
1. `python runs/verify_bake.py` — baked file reproduces the evaluated variant to the coin
2. `build_submission.validate(path)` — official runner, 720 steps, DONE/DONE, worst case < 200 ms
3. stdlib only, no `__file__`, no network

An unmodified public build whose own notebook log already shows that check does not need it repeated.

---

## 9. Closed levers (2026-09-25) — the guard is exhausted on this base

- **Guard knob fine sweep `g6`** (129,591 games): margins 11-17 and price floors p5/p8/p15 are all
  within +/-0.22pp of the shipped margin 14, top z=2.58 on an 11-variant sweep. Nothing to win.
- **Why**: `runs/discard_probe.py` shows Frontier only discards **5.5 units/game (all WHEAT, ~$150)**
  under the guard, 5.8 without it. The shed leak is closed on this base. The guard is worth +27.5pp on
  cha22 and +1.2pp here for exactly that reason — **expect large guard gains only on bases that leak**.
- **`opt/sale_advance.py` — sell before the opponent's predicted dump: CLOSED, negative.**
  Every setting lost, monotonically worse with more lead: lead 0 -2.89pp, lead 1 -14.75pp (z=-6.34),
  lead 2 -18.75pp, min_events 2 -28.75pp (z=-10.58). Dumping a stack early walks our own price down the
  glut curve, and these tapes are tuned to sell *after* town demand restores the price. Do not retry
  advance-style sale timing.
- **Liquidation**: $0 unsold at season end, every game. Nothing there either.
- **Remaining loss profile**: median loss $557, 46.8% of losses under $500. Worst matchup
  c-koshinm-0921 at 35.1% (median deficit $430) though it is 27.8% overall — non-transitive.

**ENGINE GOTCHA:** market orders are **lists** `["SELL", item, qty]`. `_parse_order` returns None for
any other shape and drops the order **silently**. Dict-shaped orders produced deltas of exactly 0.00
with z=0.00 across 8 variants and 8,320 games. *A delta of exactly zero means your layer is not
running.* Also: `pathlib.write_text()` without `encoding="utf-8"` corrupts source files on Windows.

## 9b. Daily survey, 2026-09-25

Five reruns, no genuinely new strong build. **tetsutani's new build, guru's Master Engine V3 and our
`c-cha22` are the same file** (sha `127ed3e6`) -- always hash before treating a rerun as new.
New and installed: `c-evgen-0924`, `c-utils-v1` (old pipe-7 tape family, $187k vs starter).

**Discard-probe screen** (`runs/discard_probe.py`, the cheap "is this base worth guarding?" test):
every current base leaks only 7-17 WHEAT units/game (~$150-400). frontier-0923 10.3, evgen 6.8,
utils-v1 17.0, shepherds/harvest-ledger/v15stack/late-v16/herdsafe-v3 all 10.3 (same Metav4 lineage).
**No current base leaks enough for the guard to matter** -- it is worth +27.5pp only on a leaky base
like cha22. Screen every new base this way before spending farm time on a guard sweep.

## 9c. Running now

- **`g5`** (35 kernels × 150 min, seeds 2.3M; local arm on 2.4M): 15 candidates — our champion
  `guard:c-frontier-0923:14`, five 09-24 bases with and without the guard (`c-masterhybrid-2965`
  = Frontier's parent, `c-shepherds-0924` = carries the forecast overlay, `c-harvest-ledger-0924`,
  `c-pop-robust-0924`, `c-cha22`, `c-pioneers-c2`), plus guarded Herd-Safe v3 and v15stack —
  against a **fixed 10-agent opponent field disjoint from the candidates**.
  Question: does any base beat Frontier-0923, and does guarding a forecast-carrying base beat ours?

## 10. What to do next

1. **Base selection is the only lever with proven returns.** The best public base improved ~15pp in a
   single day (frontier-0922 74.5% -> frontier-0923 89.8%), while every wrapper we own is worth 0-2.5pp
   on it. Survey, test, ride the best base; guard it only if `runs/discard_probe.py` shows it leaks.
2. Re-survey the Code tab **daily** — the best available base changed on three consecutive days.
   `kaggle kernels list --competition kaggriculture --sort-by dateRun`, then `runs/fetch_out.py <ref>`.
3. If nothing beats the champion, the next lever is porting the **opponent-sale forecast** as an
   external wrapper (like the guard), so it can ride on whatever base is currently best.
4. Reserve the final two slots for 2026-09-30, since only the latest 2 count.
5. Open question worth real effort: build a **live-correlated evaluator**. Offline win rate vs public
   agents is a weak predictor. Candidate approach: score candidates against the *recorded actions* of
   currently top-rated live teams from `data/top10/` and the episodes dataset, rather than against
   public agents only.
