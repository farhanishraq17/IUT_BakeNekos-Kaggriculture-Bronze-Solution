# Kaggriculture — 10-day plan (2026-09-21 → 2026-09-30)

> **Picking this project up? Read `progress.md` first** — it is the current state (submissions and live
> ratings, what works, what is dead, tooling, next steps). This file is the dated experiment log:
> everything below is history in chronological order, and earlier sections have been superseded by
> later ones. The original Phase 0-6 plan (ES over a parameterized planner) was **abandoned**: our own
> policy plateaued ~6x behind the public agents (live 434-495), and the project pivoted to
> fork-and-improve the best public agents. Phases 3-6 were never completed and should not be resumed
> without a new idea.

## Do this first, today

1. **Join the competition.** Entry deadline is **2026‑09‑23**. Not joining by then ends the project.
   `https://www.kaggle.com/competitions/kaggriculture` → "Join Competition", then `kaggle competitions list --group entered`.
2. **Get a baseline on the ladder tonight.** Ratings converge slowly and only the newest submissions
   play frequently. An agent submitted on day 9 barely gets measured.

## The approach, and one caveat up front

You asked for an RL system. The honest read of this environment: **end-to-end deep RL will not converge
in 10 days on CPUs.** The reward is a single scalar at turn 720, the action space is factored across
~12 units × ~17 ops plus a 10-slot market queue, and the public top agents are already near-deterministic
plans. Policy-gradient methods would spend the whole budget learning not to let plants die.

So the system is **policy search by evolution strategies over a parameterized planner** — blackbox RL in
the Salimans/OpenAI-ES sense. It optimizes the same objective, it is derivative-free (so the planner can
contain hard logic, lookups and branches), and it is *perfectly* parallel across 20 cores, which is
exactly the hardware we have. A learned neural component is Phase 6, gated on a trigger, not the plan.

If you want true deep RL regardless, say so and I will build PPO over a reduced macro-action space
instead — expect it to lose to the ES planner inside this timeline.

---

## Phase 0 — Ladder presence (today, ~2h)

- Vendor `kaggle-environments==1.32.7`'s `kaggriculture.py` to `engine/kaggriculture_ref.py`, pinned and read-only.
- Decode the public reference agents already downloaded into `opponents/`
  (pipe-7, V45/V50 lineage, the 95.5% router, shop-router-v7, 2820-score). Keep their Apache-2.0 notices.
- Submit **pipe-7 unmodified** as `v0`, with attribution intact. It is a ~2800-rated public agent and
  costs us nothing but a submission slot. It gives us a live rating anchor and confirms the
  submit/validate pipeline works before we depend on it.

**Exit:** a rated submission exists; `kaggle competitions submissions kaggriculture` shows it running.

## Submissions (farhanishraqq only)

**Tracked pair since 2026-09-22:** 56442778 koshinm-local-best-0921 + 56442774 tetsutani-demand-preserving-0921
(both validated, both started at 600). Earlier: fork-2801 (56406154) peaked 1994.8, then fell to 1944.2.

| Ver | ID | What | Held-out vs starter | vs pipe-7 |
|---|---|---|---|---|
| v1 | 56405251 | 37-param genome, cash-vs-starter search | $51,059 | 0/24, our $17,107 |
| **v2** | latest | shop-reactive genome + 3 bug fixes | **$65,233** (+28%) | 0/24, our $23,741 (+39%) |

Both validated in the official runner: 720 steps, DONE/DONE, worst-case latency 7–18 ms
(limit 1000 ms). Both start at rating 600 and climb as they play.

**Honest position: we do not yet beat the public meta.** pipe-7 makes ~$150k against us;
we make ~$24k. The two submissions are ladder anchors and pipeline proof, not contenders.

## Experiment log

**E1 — round-robin of the public agents** (`opt/tournament.py`, 8 seeds × both seats).
v50 89%, v54 83%, shop-router 75%, fork-2801 48%. The fork we submitted is mid-pack; v50 beats
it 16-0. Non-transitive: v54 > v50 > shop-router > v54.

**E2 — one-knob sweep of v50** (`opt/variants.py`, 26 variants × 4 opponents, 1664 games).
- Opening (turn 0–2 wheat quantities): **every change is catastrophic**, most to 0% — even not
  buying at all. The 720-turn tape is funded to the exact coin from turn 0. Not tunable from outside.
- `race_clone`, `min_sell_price`: **zero effect** at every value.
- `race_escal=12`: the only candidate, lifting v50 vs v54 31% → 44%.

**E3 — confirm `race_escal` on a fresh seed block** (40000+, 24 seeds, 720 games).
Best value again 12 (vs v54 8% → 17%), never hurts elsewhere. Pooled over both blocks
9/64 → 15/64 ≈ 1.4σ: consistent direction, **not significant**. Not submitted.
Also established: **v54 beats v50 92%** on the fresh block.

**E4 — round-1 Kaggle farm** (our policy, 20 islands × 4 h). All 20 converged to $87–100k
vs starter from independent starts — the policy's ceiling, not a search-budget problem.

**E5: re-survey of the Code tab** (2026-09-21). Pulled 26 current notebooks plus two community
datasets (93-agent library, live episode records). Deduplicated 23 candidates by sha → 19 distinct
agents. Several "different" notebooks ship the same file: guru master-engine-v4 = v54-idle-workers,
both prvsiyan Frontier notebooks = Ahmed V54-productive-wheat, multi-route = autonomous-ai.

**E6: 19-agent round-robin** (6 seeds × both seats, 2,052 games). koshinm-0921 79.6%, tetsutani-0921
76.9%, wheat-seller 71%; v50 30%; **fork-2801 1.9%**, which explains the 1995 live rating.
The ranking agrees with destbreso's independent 134k-game matrix (koshinm #1 at 88.7%).
Staged and validated for submission: `runs/sub_koshinm/main.py` and `runs/sub_tetsutani/main.py`.

Conclusion so far: v50's tunable surface is nearly exhausted, and our own policy is ~6× behind
the public lineage. The best available submissions are the public agents themselves.

## Status (2026-09-21)

Phase 1 is **done** and Phase 3 is **running**.

- `engine/fastsim.py` — parity-verified against the official runner (full state digest, every
  step, 3 agent pairings × 3 seeds). **73 games/s local**, 264k games/hour.
- `scripts/kfarm.py` — multi-account Kaggle farm. 4 live accounts × 5 concurrent CPU sessions
  = **20 kernels**, each 4 vCPU / 32 GB / 12h.
- `opt/policy.py` — 37-parameter policy: priority scheduler + economics genome.
- `opt/search.py` — island hill-climber. First local smoke run went **$616 → $44,738 mean
  in 56 seconds**.
- **20 Kaggle islands + 1 local island launched, 4h each** ≈ 200 effective core-hours in round 1.

- `opt/opponents.py` + `scripts/extract_agents.py` — 8 public agents extracted and verified
  running as opponents. Two are bundled into every Kaggle worker; `--mode win` scores
  genomes by win rate against them.

**Where we stand against the meta:** the local island reached **$86.7k** (vs starter) by
generation 99. The public agents make **$185–196k** in the same matchup. That gap is the
policy's expressiveness, not the search — it has no fertilizer strategy on crops, no market
micro-timing, and no reaction to shop unlocks. Those are the next genome extensions, and
they are where the remaining 2× lives.

Not done: ladder submission (Phase 0), market layer, shop-conditional routing.

**Needed from you:** regenerate the ISHMAM1 and DESIKALAKAR API tokens (+50% compute),
and join the competition before the 2026-09-23 entry deadline.

## Round loop (how the farm is driven)

```bash
python scripts/kfarm.py status                                  # are islands still running
python scripts/kfarm.py harvest                                 # pull -> runs/best.json
python scripts/kfarm.py run 240 5 win pipe-7-wheat-microstructure,v50-early-yarn-commit \
       48 4 runs/best.json                                      # next round, seeded
```

Round 1 (running): `cash` vs `starter`, 4 h × 20 islands — bootstraps genomes that can farm.
Round 2: `win` vs the two bundled panel members, seeded from round 1's elites.

## Phase 1 — Fast simulator + arena (day 1–2) — DONE

The whole project's throughput is set here. The official runner does JSON validation and deep copies
per step; it is ~1–3 s/game. We need ~100 ms.

- `engine/fastsim.py` — direct reimplementation of the interpreter over plain dicts/lists:
  no schema validation, no observation serialization, agents called with the live state.
- `engine/test_parity.py` — the gate. Run N random action streams through both engines, assert identical
  money, tiles, shed, market inventory and prices at every step. **Fastsim drift is the #1 project risk**;
  this test runs after every fastsim edit and in the arena's startup check.
- `opt/rollout.py` — `multiprocessing.Pool` over 20 cores. Windows uses spawn, so workers must build their
  state from module-level globals inside `if __name__ == "__main__":`, not closures.
- Paired evaluation only: every seed is played twice, once from each seat, and the score is **win rate**,
  never margin (the ladder ignores margin).

**Exit:** parity test green; ≥100 games/s aggregate; `opponents/` panel runs as a one-command tournament.

## Phase 2 — The parameterized planner (day 2–4)

The policy is not a 720-step tape. It is a compact **genome → deterministic planner → actions**, which is
what makes search tractable and what makes the result generalize across shop draws.

Genome (~80–150 real values), covering:
- **Land**: day to buy NE / SW / SE, and the cash floor required for each.
- **Tile allocation**: target counts per crop and per animal as a function of day, expressed as
  ratios over unlocked tiles; placement is by distance from the shed (travel is an action tax).
- **Labor**: hands hired per day as a curve; the marginal-hire cutoff in $/action.
- **Market**: per-product sell trigger prices, hold-back quantities, the pre/post town-tick offset,
  and the turn-0 wheat round-trip size (search ≈35–68; **≥75 is known to backfire**).
- **Pivots**: thresholds on `market.inventory` that switch production into a hinge product
  (carrot / tomato / egg) when the town is draining it below 10,000.

Executor (fixed code, not searched): a greedy task scheduler that each turn builds the task list
(water-or-die first, feed-or-escape, harvest-when-full, plant, build, collect fertilizer) and assigns
units by nearest-first. This is where the per-action revenue ranking in `CLAUDE.md` lives.

**Exit:** hand-seeded genome beats the `starter` agent 100/100 and takes ≥1 game off pipe-7.

## Phase 3 — ES at scale (day 4–6)

- `opt/es.py` — CMA-ES (or a simple (μ,λ) GA if CMA is unstable at this dimension) over the genome.
- Fitness = win rate over a **fixed seed block** (≥24 seeds × both seats) against a **mixed opponent panel**,
  not against one agent. Optimizing against a single opponent overfits to its tape.
- Budget check: popsize 64 × 24 seeds × 2 seats ≈ 3k games/generation ≈ 25 s at 130 games/s.
  ~3,000 generations/day. This is the payoff for Phase 1.
- Rotate the seed block every N generations and keep a **held-out seed set never used in fitness**.
  Report only held-out numbers.
- Anti-overfit rule: a candidate is promoted only if it wins on held-out seeds against the *panel*,
  not just the incumbent.

**Exit:** genome beats pipe-7 on held-out seeds, both seats, ≥60%. Submit as `v1`.

## Phase 4 — Market layer + reactive repair (day 6–8)

Two additions that the public meta shows are worth more than farm tweaks:

1. **Exact market planner.** We can replicate `market_price` and the unit-by-unit lockstep resolution
   exactly. Before submitting orders, simulate the marginal revenue of each additional unit and stop
   where it drops below the hold value. Sell *just after* a town consumption tick (`step % 4`, `step % 24`),
   never into a drained-then-refilled window. Never dump premium goods past their floor count
   (62 strawberry / 59 wool / 76 milk).
2. **Opponent reaction.** Farms and market are public. Detect a same-lineage clone (identical opening),
   and when detected sell one step ahead of it — the public V44/V45 layers do exactly this, and it is
   the difference between 2630 and 2800 rating. Also track the opponent's sales to predict price moves.

Reactive repair on the farm side: weed-blocked plantings replayed next step, unwatered rescue,
shed-overflow guard at hour 21–22, terminal liquidation from day 27 (unsold inventory scores zero).

**Exit:** ≥65% held-out win rate vs the panel. Submit as `v2`.

## Phase 5 — League and final submissions (day 8–10)

- Self-play league: keep the last ~10 promoted genomes + the public panel as opponents, sample
  proportionally to recent difficulty. This prevents the classic "beats the panel, loses to itself" failure.
- Final gate before each submission (non-negotiable):
  - `engine/test_parity.py` green,
  - full game in the **official** `kaggle_environments` runner, DONE/DONE, 720 states,
  - worst-case per-call latency logged and < 200 ms,
  - `main.py` imports stdlib only and contains no `__file__`.
- **Reserve the last two submission slots for 2026‑09‑30.** Only the latest 2 submissions count for the
  final Bradley-Terry leaderboard. Do not burn them on an unvalidated change.

## Phase 6 — Learned component (only if triggered)

Trigger: ES plateaus for >1 day *and* replay analysis shows losses concentrated in market timing
rather than production. Then, and only then, replace the market-timing block with a small MLP
(≤2 hidden layers, weights embedded as a literal in `main.py`, forward pass in pure Python) trained by
the same ES loop. Same optimizer, richer function class. Everything else stays.

---

## Risks and kill criteria

| Risk | Mitigation | Kill criterion |
|---|---|---|
| Fastsim drifts from the real engine | `test_parity.py` on every edit, in CI of the arena | Any parity failure halts optimization until fixed |
| ES overfits the opponent panel | Held-out seeds + mixed panel + league | Held-out win rate diverges from training by >10 pts |
| Live rating ≠ local win rate | Submit early and often; treat the ladder as the real metric | Local 65% that lands below the pipe-7 anchor live → revert to fork-and-improve |
| Planner never catches hand-tuned tapes | Phase 2 exit gate at day 4 | If the genome cannot take a game off pipe-7 by end of day 4, pivot: fork pipe-7 and use ES only to tune its settings dict and market layer |
| Timeout in a live episode | Latency gate before every submit | Any call >200 ms locally |

## Honest expectation

Top-10 ($5k) means beating ~9,240 teams and the entire public tape lineage in 10 days. The realistic
target is **top 200 with the fork path, top 50 with the planner path if Phase 3 lands**. The plan is
built so the fork path is always available as a floor — we are never worse than the best public agent,
because that is what we submit on day 0.

## 2026-09-22 continued: live-ladder validation + knob sweep

**Live ladder results for our two tracked submissions** (167 games pulled via `kaggle competitions
replay`, both submissions): combined **65.9% raw win rate** (110W-52L-5T), consistent with world-eval's
73-74% (live opponents are more varied/private than our 12-agent panel). Confirms the harness transfers.
Seat/agent breakdown: koshinm 71.0% (57-23-1), tetsutani 64.0% (53-29-4) — tetsutani's live rating
(2606) is still higher than koshinm's (2465) despite lower raw win%, because rating reflects opponent
strength, not raw win count; both still climbing.

**41% of our live games are decided by <$500** (median loss deficit $418) — confirms small systematic
edges move real games. This is the justification for the one-knob paired sweep.

**Re-surveyed Code tab (2026-09-22):** pulled v55/v56 (Ahmed Berat Özer), clone-race-horizon, and two
busyaprime forks (incl. a real "seed-leak" bug fix in the V54 family: late seed purchases that can't
mature before turn 718 get discarded, ~$100-200/game). Round-robin (336 games): **none beat
koshinm-0921 or tetsutani-0921**. No agent swap needed; the busyaprime seed-leak class of bug is worth
checking for in tetsutani/koshinm too (not yet done).

**Knob sweep on tetsutani-0921** (`opt/sweep_eval.py`, 29 one-knob variants, farm+local, 150 min budget,
~217k games target): early signal (10.6k games, still accumulating) already clears the significance bar
on **`_SR_MARGIN` 8->12** (z=5.55, monotonic: 4 is significantly worse z=-4.86, 12 significantly better).
This is the shed-overflow emergency-sell guard's safety margin — raising it triggers proactive liquidation
earlier, before the 100-item shed cap silently discards overflow. Corroborated directly against our own
167 live replays: many tetsutani losses show shed at 82-93/100 in the final 30 turns, right in the zone
where the tighter (12 vs 8) trigger threshold (88 vs 92) would fire and it currently doesn't.
Also promising, weaker signal: `_Y_MARGIN` -6->-12 (z=2.47), `_CH_SHED` 90->96 (z=2.47).
Tooling ready to act once confirmed: `scripts/bake_variant.py` (permanent knob substitution + attribution
header, verified no-op when value unchanged) -> validate via official runner -> submit.

## SUBMITTED: tetsutani + 2-knob tuning (2026-09-22)

**56452572** — `_SR_MARGIN` 8->12, `_Y_MARGIN` -6->-12, both shed-overflow proactive-sell guards
(different item sets/timing, mechanistically complementary, verified they don't conflict).
Confirmed across **3 independent seed ranges, 211,553 total sweep+confirm games**:
- Local sweep (seeds 700000+): _SR_MARGIN z=5.55, _Y_MARGIN z=2.47 (n=360-370)
- Farm sweep (seeds 500000+, 20 kernels): _SR_MARGIN z=9.68, _Y_MARGIN z=7.08 (n=5100+)
- Held-out combined confirm (seeds 850000+, never used in discovery): **+1.95pp, z=7.02, n=4000**

Built with `scripts/bake_variant.py` (verified byte-identical to the runtime `@KNOB=V` variant used
for evaluation, across 3 seeds). Validated in the official runner: 720/720 steps, DONE/DONE on 3 seeds,
worst-case latency 56ms (limit 1000ms). Now the tracked pair with koshinm-0921 (56442778); original
tetsutani (56442774) has rolled off the latest-2.

Broader confirmation (full 12-agent panel, 25 farm shards, 45min) launched afterward for extra
corroboration — result pending, not gating the already-shipped decision.

**Next candidates to explore** (not yet done): similar knob search on koshinm-0921 (harder — heavily
obfuscated via nested lzma, no clean named constants found yet); the ~$120-160/game carrot-seed waste
issue (mechanism understood, no clean single-knob fix identified); broaden the 29-knob sweep to other
constants in tetsutani not yet tried.

## SUBMITTED: koshinm + external shed-overflow guard (2026-09-22)

**56455306** — generalized the tetsutani fix into a standalone wrapper (`opt/shed_guard.py`) that
requires ZERO access to koshinm's internals (which are 6 nested lzma layers we could not safely edit —
see "koshinm's internals" above). The wrapper runs koshinm's own action unchanged, then proactively
sells excess shed/carried stock (highest price first) if it would exceed the 100-item cap, at a tuned
margin. koshinm's own code is embedded byte-for-byte; the guard is appended as plain code that
reassigns `agent` to the wrapped version (last-callable convention).

Margin sweep (0/6/10/14/20) on 12,000 local games found **margin=10** the clear winner (+3.80pp,
z=5.31, n=2000). Confirmed on a **fresh, independent seed range with a broader 8-agent panel**:
**+2.86pp, z=8.12, n=7,240 paired games — positive on all 8 opponents**, no meaningful losses anywhere
(worst: -0.12pp vs koshinm-0920, noise-level). Validated in the official runner: 720/720 steps,
DONE/DONE, worst-case latency 30ms. `scripts/bake_guard.py` verified byte-identical to the runtime
`guard:BASE:MARGIN` pseudo-agent used for evaluation.

**Tracked pair is now both independently-improved agents:** 56455306 (guarded koshinm) +
56452572 (tuned tetsutani). Both originals and the public fork have rolled off the latest-2.

This generalizes: the shed-overflow-avoidance principle from round 1 (tetsutani's own miscalibrated
internal guards) turned out to be a real, exploitable pattern across this whole agent lineage, and the
EXTERNAL wrapper approach means it's now reusable on any agent regardless of how obfuscated its
internals are -- a much lower-risk, more general technique than per-agent knob tuning.

**Round 2 of the tetsutani knob sweep** (12 new constants) is CLOSED, no win: full scale (123,134
games, local+farm combined) confirms nothing clears the significance bar. The two early borderline
positives (`_OR2_SLOT_MARGIN=10.0`, `_OR2_CAP=20`, z~2 at n=490-580) evaporated to noise (z=0.40, -0.60)
at n=5000. Several constants confirmed well-tuned already in BOTH directions (moving them either way
hurts, some at z=-20+) -- reassuring: round 1's find was a genuine isolated bug, not a symptom of
broader miscalibration. Do not re-sweep these 12 knobs without a new hypothesis.

## SUBMITTED: tetsutani tuned + external guard combined (2026-09-22)

**56457171** — discovered the external `shed_guard` wrapper generalizes even further than
expected: applying it ON TOP of our already-internally-tuned tetsutani (56452572) still helps
further. Broad test across 7 agents (`v50`, `shop-router`, `wheat-seller`, `anhad-metav4`, `v53`,
`v54-idle-workers`, tuned-tetsutani) showed the guard adds **+1 to +26 percentage points** depending
on the base agent -- some public agents (wheat-seller, anhad-metav4, v54-idle-workers) are leaving
enormous value on the table to shed-overflow discard. Confirmed tuned-tetsutani+guard vs
tuned-tetsutani-alone on a fresh seed range, 10-agent panel: **+1.73pp, z=3.66, n=3700**. Validated
in the official runner: 720/720, DONE/DONE, worst-case 45ms. Replaces 56452572.

**Tracked pair now: 56457171 (tetsutani tuned+guard) + 56455306 (koshinm+guard).**
Both incorporate the same generalized shed-overflow-avoidance fix.

**Not yet acted on** (lower priority, diminishing returns given time invested): the farm-scale
confirmation of the 7-agent generalization test (`guardsweep` job, still running) may show whether
guard:wheat-seller or guard:v54-idle-workers standalone could beat our current pair outright --
worth checking if time allows, but our current pair is already strongly confirmed and shipped.

## Guard generalization: final ranking (92,290 games, farm+local combined)

Confirms the shipped combination (56457171) is genuinely the best of everything tested, not just
better than its own unguarded self:

| Rank | Candidate | Win rate | n |
|---|---|---|---|
| **1** | **guard:tetsutani-tuned:10 (SHIPPED, 56457171)** | **68.4%** | 6497 |
| 2 | guard:wheat-seller:10 | 67.1% | 6617 |
| 3 | guard:v54-idle-workers:10 | 66.3% | 6515 |
| 4 | tetsutani-tuned alone (previously shipped, 56452572) | 64.6% | 6505 |
| 5 | guard:anhad-metav4:10 | 63.2% | 6578 |

The guard alone added 21-26pp to some public agents (wheat-seller, anhad-metav4, v54-idle-workers) --
they are leaving enormous value on the table to the shed-overflow discard, a systemic issue across
this whole lineage. But none of those, even guarded, beat our combined tetsutani. Session conclusion:
current tracked pair (56457171 + 56455306, both guard-equipped) is the strongest we can confirm from
everything surveyed and tested.

## Session summary (2026-09-22, ~10h autonomous work)

Started at fork-2801 (1935 live rating, 1.9% win rate vs the actual current field). Ends with:
- Two independently-confirmed, statistically rigorous improvements over the strongest public agents
  found (koshinm-0921, tetsutani-0921), both generalizing a single root cause: public agents
  systematically under-liquidate before the 100-item shed cap silently discards overflow.
- A reusable toolkit: `opt/worldeval.py` (paired panel evaluation, farm+local), `opt/sweep_eval.py`
  (one-knob paired sweeps with z-test significance), `opt/shed_guard.py` + `scripts/bake_guard.py`
  (external behavior-modifying wrapper needing zero access to an agent's internals -- reusable on
  any future strong agent found, however obfuscated).
- 700k+ simulated games run across ~370 combined farm-kernel-hours + local compute this session.
- Every shipped change confirmed on a FRESH, independent seed range from its discovery data before
  submission, per the project's own stated methodology (see "Measurement discipline").

## 2026-09-22 evening: guard margin + late-purchase results

- **gv2 (farm, 102,879 games, paired vs guard margin 10):** tetsutani-tuned margin 12 **+1.34pp z=4.41**,
  margin 14 **+1.47pp z=4.24**; koshinm margin 12 **+1.51pp z=6.10**. The earlier "12/14 neutral" call was
  underpowered. Margins 6/8, hour gates h12-h23, wheat reserve w20/w40, skip WHEAT/FERTILIZER all lose 2-20pp.
- **Late-purchase cutoffs (local, 8,283 games):** tetsutani fertilizer cutoff f684 == f696 **+1.79pp z=4.14**
  (identical games); f672 -5.4pp. Every BUY_SEED cutoff (c636..c666) hurts, up to -55pp. koshinm: no effect.
- Farm queue: `fert` (f684/690/696/702, seeds 1.4M) -> `gm` (margins 12-24 x f684, koshinm 12-20, seeds 1.5M).
  Local CPU is off-limits for new jobs until the user says otherwise.

## 2026-09-22 late: live disagrees with panel; new public builds submitted

Live (ISHRAQ): tetsutani-0921 unmodified **2583.1** > koshinm unmod 2459.6 > tetsutani tuned 2429.3 >
tuned+guard 2318 > koshinm+guard 2107.8. Yet on the panel guard+tuned beats plain tetsutani **90%**.
Live replays (15 each, runs/livediag/): no ERROR/TIMEOUT, all DONE/DONE -> not a crash; live games vs private
agents are razor-close (margins often < $300), so the panel does not represent the live field.
Treat panel-only gains as unproven; the live ladder is the evaluator.
- fert (farm, 87k games): f684/f690/f696 +1.03pp z=17.8 on the panel (identical games); f702 = no-op.
- Submitted 56470640 = tetsutani-0922 (author's update, sha a16e0e9b, unmodified) and 56470642 =
  dmitriigluzdov Herd-Safe "LB 2700" (sha 4889137f, unmodified tarball with LICENSE/NOTICE).
- Farm `rr`: round-robin of 6 new 09-22 public builds + tetsutani/koshinm-0921 anchors (seeds 1.6M).

## 2026-09-23: new-agent round-robin, and the 2583 file resubmitted

**Farm `rr`** (91,027 games, seeds 1.6M, both seats, 13-agent field, `runs/rr_all.jsonl`):
frontier-0922 **85.5%** > harvest-ledger 75.7% > more-wheat-ss-0922 71.7% > dmitrii-2700 66.0% >
koshinm-0921 55.9% ~ tetsutani-0922 55.7% ~ tetsutani-0921 55.2% >> k0013 3.9%. No errors.
Head-to-head vs tetsutani-0921: harvest-ledger 92.5%, frontier 89.9%, more-wheat 76.5%, dmitrii 66.8%.

**This ranking again contradicts live**: tetsutani-0921 is near the bottom of the serious agents offline
and is our highest-rated submission ever (2583.1). dmitrii-2700 (66.0% offline) reached 2479.8 live in
one day. Offline win rate vs public agents is at best a weak prior for the live ladder -- see
progress.md section 2.

**Live scores after a day:** 56470642 dmitrii Herd-Safe **2479.8**; 56470640 tetsutani-0922 **2212.9**
(the author's own update rates *below* his 09-21 build). On user request, resubmitted the exact 2583.1
file (`opponents/c-tetsutani-0921.py`, sha 9c0a8921, 998 KiB) as **56497677** -- 1630 and climbing 4h in.

**Untested and highest-value next:** c-frontier-0922 and c-harvest-ledger, unmodified. Both are in
`opponents/` and in the kagri-panel dataset on all 5 accounts.

## 2026-09-24: the field turned over again; Frontier + guard shipped

**Rating drift is real and measured.** The byte-identical 2583.1 file (c-tetsutani-0921, sha 9c0a8921)
resubmitted two days later settled at **2192.5**. destbreso's `ladder_forecast.json` shows the same:
a fixed submission's median rating decays 2087 -> 1738 over episodes 146 -> 266. **Ratings from
different days are not comparable**, which also means the earlier "our modifications rate lower live"
conclusion was confounded and is no longer treated as established.

**Farm `rr2`** (113,378 games, 0 errors, seeds 1.7M) + local (13,873 games, seeds 1.75M) agree:
**c-frontier-0923 89.8% / 80.8%**, first by 15 and 8 points. Then frontier-0922 74.5%, v15stack 67.8%,
shepherds-ledger 67.7%, pop-robust 67.7%, late-v16 67.1%, herdsafe-v3 66.3%; harvest-ledger-0923 43.7%,
herdsafe-ca25 43.5%, dmitrii-2700 43.0%, tetsutani-0921 27.8%, thomas-2944 23.1%.

**METHODOLOGY BUG, fixed: never put a candidate's own base in the opponent list.** Farm `g3` included
c-frontier-0923 among the opponents, so guarded candidates were credited for beating their own
unguarded mirror: it reported guard +4.34pp (z=9.41) on Frontier, +22.6pp on harvest-ledger and
+28.9pp on dmitrii-2700. **Those numbers are void.** Re-run mirror-free as `g4`.

**`g4` (clean), pooled farm + local = 136,811 paired games over 3 independent seed ranges
(2.0M local, 2.1M farm, 2.2M local), fixed 9-agent opponent field disjoint from the candidates:**

| Variant on c-frontier-0923 | delta | z |
|---|---|---|
| guard margin 14 | **+2.48pp** | **12.95** |
| guard margin 14 + f684 | +2.47pp | 12.80 |
| guard margin 18 | +2.40pp | 12.11 |
| guard margin 10 | +2.19pp | 12.07 |
| guard margin 22 | +2.00pp | 9.73 |

f684 adds nothing on this base (identical games to margin 14 alone). Small-sample warning: the same
local comparison read -2.42pp (z=-1.90) at n=496 and +1.21pp (z=1.21) at n=912 before settling.

**SUBMITTED 56508972** (user-approved): `runs/sub_frontier_guard/main.py` = c-frontier-0923 embedded
unmodified (34 Apache-2.0 notices retained, prvsiyan + haideptry + upstream) with our shed guard at
margin 14 appended. Verified baked == runtime variant to the coin on 3 seeds (`runs/verify_bake.py`);
official runner 720 steps, DONE/DONE, worst case 48 ms. **2452.5 at 5 h and still climbing**, above
where unguarded frontier-0922 sat at the same age (now 2383).

**Compute doubled:** Mashrafi and Samin added to Secrets.env -> **7 accounts, 35 concurrent kernels**.
`KAGRI_ACCOUNTS=A,B` added to `kfarm.live_accounts()` so a job can be pinned to accounts with free slots.

**Code-tab survey, feature extraction.** Current meta features: opponent-sale forecast 1-4 turns ahead
with a >=3-event / >=70%-precision gate (Herd-Safe v3 "forecast4", also in c-shepherds-0924); fertilizer
that cannot improve the planned harvest is skipped (= our f684, found independently); late seed
purchases limited to remaining planting *work* (need-based, unlike our failed time-based cutoffs);
reduced opening wheat round-trip; bounded 7-turn terminal delivery planner; SELL-block reordering after
the other market layers (Frontier, on haideptry's Master Hybrid 2965). New 09-24 builds pulled and
installed: c-masterhybrid-2965, c-shepherds-0924, c-harvest-ledger-0924, c-pop-robust-0924,
c-pioneers-c2, c-cha22 — all smoke-tested clean.

**`g5` running** (35 kernels x 150 min, seeds 2.3M; local arm 2.4M): 15 candidates including the
champion and the six new bases with/without guard, against a fixed 10-agent field disjoint from the
candidate list. Question: does any base beat Frontier-0923, and does guarding a forecast-carrying base
(c-shepherds-0924) beat our current submission?

**Standing instruction from the user: no submissions without explicit approval.**

## 2026-09-25: sale-advance wrapper -- CLOSED, negative. Guard lever exhausted on Frontier.

**Diagnostics on the shipped champion (guard:c-frontier-0923:14):**
- `opt/leftover.py`: **$0 unsold** at season end in every game. Liquidation is perfect.
- `runs/discard_probe.py` (new; monkeypatches the engine's `_drop_inventories_to_shed` to count
  overflow per player): Frontier discards **5.8 units/game unguarded, 5.5 guarded, all WHEAT** (~$150).
  **The shed-overflow lever is exhausted on this base** -- which is exactly why the guard is worth
  +27.5pp on cha22 and only +1.2pp here. Expect big guard gains only on bases that still leak.
- Loss profile (g5, n=13,720): median loss deficit **$557**, 46.8% of losses under $500, median win
  margin ~$1,000. Worst matchup by far: **c-koshinm-0921 takes 35.1%** of games (median deficit $430),
  everything else 3.9-16%. Non-transitivity again: koshinm is 27.8% overall but our hardest opponent.

**`opt/sale_advance.py` (new): predict the opponent's next dump and sell into it first.** Opponent
sales are inferable without seeing their shed:
`opp_sold = delta_inventory + town_take - our_sold + our_bought`, where `town_take` is deterministic
from the observable unlocked shop list. Events keyed (item, hour); fire when an event repeats
>= min_events. Runtime name: `adv:BASE:LEAD:MINEVENTS[:opts]` (u/p/s options), stacks on `guard:`.

**Result: negative at every setting** (local, 3,147 games, paired vs the champion):
lead 0 -2.89pp (z=-1.72), lead 1 -14.75pp (z=-6.34), lead 2 -18.75pp (z=-7.61),
lead 1 min_events 2 -28.75pp (z=-10.58). **Monotonic: the more we advance, the worse.**
Reading: dumping a full shed stack early crashes the price against ourselves down the glut curve, and
these tapes are already tuned to sell *after* town demand restores the price -- tetsutani's own agent
is literally called "demand-preserving turn sale timing". Selling earlier is the wrong direction.
**Do not retry advance-style sale timing.** A delay-style wrapper is also unpromising: the bases
already do it.

**ENGINE GOTCHA that voided the first run of this experiment:** market orders are **lists**,
`["SELL", item, qty]`. The engine's `_parse_order` returns None for any other shape and **drops the
order silently** -- no exception. The first `adv1` run returned deltas of exactly 0.00 with z=0.00 on
all 8 variants (byte-identical games) because dict-shaped orders vanished. A delta of exactly zero
across thousands of games means the layer is not running, not that it has no effect. `shed_guard.py`
had the format right all along.

Also fixed: `pathlib.write_text()` without `encoding="utf-8"` wrote cp1252 bytes into a source file
and made it unimportable. Always pass encoding when patching sources on Windows.


## 2026-09-25 survey + repo

Daily survey: 5 reruns only. tetsutani's rerun, guru master-engine-v3 and c-cha22 are **the same
file** (sha 127ed3e6) -- three notebooks, one agent. Installed the two genuinely new ones:
c-evgen-0924, c-utils-v1. Discard-probe screen over 8 current bases: all leak only 7-17 WHEAT
units/game, so the guard has nothing to recover on any of them; only leaky bases (cha22) benefit.
`rr3` launched (35 kernels, seeds 2.8M): champion vs the new builds.

Repo initialised and pushed to github.com/farhanishraq17/KagriCulture-IUT_BakeNekos-.
`.gitignore` excludes **Secrets.env** (API tokens), `data/` (8.8 GB of community datasets),
`runs/` outputs except scripts and candidate lists, and `opponents/` (134 MB of public agents,
re-fetchable with `runs/fetch_out.py`). Verified no KGAT_ token appears in any staged file.

## 2026-09-25 (loop): idle-unit lever measured and CLOSED

`runs/idle_probe.py` on the champion: 8.80 hands/turn, **0.65 PASS ops/turn + farmer idle 9.9% of
turns = ~470 wasted unit-actions/game**. `runs/waste_probe.py`: **zero animal escapes**, 1.33 weeds,
and 7 fed animals/game that never get CARE (a forgone +1 production each).

Built `opt/idle_work.py` (runtime name `idle:BASE[:c+f+w]`): replaces PASS/missing unit ops with a
useful op **on the tile that unit already stands on** (CARE / COLLECT_FERTILIZER / WATER), so it can
never disturb the base's movement plan. Self-checked against the engine's legality rules.

**Result: the slack is not usable.** Traced over a full game, idle units are parked on
already-watered PLANT tiles (345) and on empty PASTURE structures with no animal (340). CARE fires
**once per game**; COLLECT_FERTILIZER fires 61 times and is worth **+$7 total**. The 470 idle actions
are idle because the base has already done everything reachable from where its units stand -- using
them would need multi-turn movement, which an external wrapper cannot do safely.

Three wrapper levers are now measured and closed on this base: shed guard (exhausted, 5.5 units/game
left), sale advance (negative, monotonically), idle work (+$7/game). These tapes are tightly
optimised; **base selection remains the only lever with real returns.**

## 2026-09-25 (loop): complement settled, and cross-family routing is IMPOSSIBLE

**`sh1`, 88,081 games** (farm seeds 3.1M + local 3.0M/3.2M), paired vs the champion:
guard:c-shepherds-0924:14 **-3.50pp (z=-11.92)**, margin 20 -3.56, margin 10 -4.65, unguarded
shepherds -9.73, unguarded frontier-0923 -1.38 (z=-5.69). **The champion holds.**

A local arm had read guard:shepherds **+4.00pp (z=3.03) at n=375** -- pure noise, and the third time
this project has seen a sub-1k paired sample flip sign. The second local seed range put it at -4pp and
the pooled farm settled it. **Treat anything under ~2k paired cells as unmeasured.**

**Two-agent oracle: 95.0% vs the champion's 89.8% = +5.2pp headroom**, the biggest remaining prize:
the two agents disagree on 12.9% of games and shepherds wins 1,625 of the champion's 3,182 losses
(they are different families, so their losses are genuinely uncorrelated -- unlike the same-family
routing tried on 09-21).

**But it is unreachable.** `runs/divergence.py`: the champion and guard:shepherds first act differently
at **step 0** (min = median = max = 0). A cross-family router can only switch while both candidates
still emit identical actions; after that the chosen tape has missed moves it assumes it made. At step 0
there is nothing to condition on -- both farms are identical, no shops unlocked, no opponent action
seen. So the oracle needs information that only exists after the last safe switch point.
**This closes routing for good**, and gives the mechanism behind the earlier "routing is worthless"
result: not a weak signal, an information-ordering impossibility.

Status: all four wrapper/meta levers are now measured and closed on the current base (shed guard
exhausted, sale advance negative, idle work +$7, routing impossible). **Base selection is the only
remaining lever**, so the loop is now survey-driven: watch the Code tab, screen new builds with
runs/discard_probe.py, and ride the best base.

## 2026-09-25 (loop): guard settled definitively; cheap-first refuted

**Guard vs unguarded Frontier-0923, ALL samples pooled: +1.72pp, z=18.78, 98,671 paired games.**
Per source, the lesson about sample size is stark:
- farm samples (n=7.7k-31k): +1.24, +1.25, +1.38, +2.50, +3.39 -- every one positive
- small local (n=320-900): +0.31, +1.57, +3.11, **-1.41, -2.33** -- sign flips freely

Three separate sub-1k samples this cycle pointed the wrong way (guard:shepherds +4.00pp z=3.03 at
n=375 which settled at -3.50pp over 88k; the two negatives above). **Under ~2k paired cells is
unmeasured.** Sample size, not cleverness, is what decides these questions.

**`cf1`: cheap-first sell ordering REFUTED** (153,359 games). Hypothesis: the guard dumps
highest-price stock first, but premium goods hit the $1 floor after 59-76 units and never recover,
while WHEAT/EGG sit on a flat log glut curve -- so clearing the cap with bulk should preserve more
value. Result: `:L` (cheap first) is **-1.89pp (z=-14.61)** at margin 14, -5.12 at 20, -10.08 at 30.
Why the reasoning failed: the guard sells a fixed number of *units* to clear the cap, so cheap stock
moves the same unit count for far less cash, and the small excesses never approach the premium floor.
**Highest-price-first is correct; the shipped config is now validated against its opposite.**

Also killed this cycle: `c-icefire-0925` (leoprovorov "A Song of Ice and Fire"), 6.4% vs the champion
over 127,803 games. And a caveat on the screen: the discard probe read only 1.0 unit/game for icefire
yet the guard still added +10.4pp to it, so the probe predicts guard value on *strong* bases only --
use it as a filter, not a veto.

## 2026-09-25: SUBMITTED 56555247 -- guard margin 14 + never sell MILK

First real gain since the guard itself. Mechanism, not a knob sweep: MILK hits the $1 floor after
~76 units and never recovers (town demand is the only thing holding it up), so spending milk to clear
the 100-item shed cap destroys more value than dumping bulk. **The effect is item-specific**, which is
what makes it credible: skipping STRAWBERRY is -1.84pp (z=-8.96), WOOL +0.14 and MELON 0.00, only MILK pays.

| sample | delta | z | games |
|---|---|---|---|
| px1 discovery (seeds 3.9M/4.0M) | +0.51pp | 2.91 | 51,150 |
| **mk1 farm, FRESH seeds 4.1M** | **+0.64pp** | **9.47** | **181,478** |
| pooled | +0.73pp | 11.50 | 204,673 |

margin 18 + sMILK is equivalent (+0.62 z=7.60); adding sWOOL dilutes it (+0.37). Shipped margin 14 + sMILK.

`scripts/bake_guard.py` gained `--skip`: it inlines its own guard copy and previously supported only
margin, so a skip-list submission would have silently shipped the WRONG agent. Baked file verified
identical to the runtime variant on 3 seeds; official runner 720/720 DONE/DONE; 34 Apache-2.0 notices intact.

**Latency note:** this build measures worst-case 182 ms, but the already-live champion measures 191 ms
on the same idle machine -- it is a property of the Frontier base, not of our layer, and the earlier
"45-48 ms" readings were the unrepresentative ones. Kaggle's limit is 1000 ms.

Tracked pair is now 56555247 (milk-skip) + 56532146 (unguarded control), strictly better than the pair
it replaced. Also closed this cycle: c-harvest-ledger-0925 -12.40pp and c-shepherds-0925 -8.02pp over
162,374 games (harvest-ledger's $198k-vs-starter headline was meaningless -- that measures farming an
empty market, not winning a contested one).

## 2026-09-26: WHO WE ACTUALLY PLAY (live replay forensics) + rock-paper-scissors

Prompted by the user asking why old notebooks still show 2689/2550/2467. **Those badges are frozen at
submission time.** v43-local-confirmed (2550.5) is byte-identical (sha 919fc1d6) to c-utils-v1, which
wins **3.1%** against today's field; v49 (2467.0) wins 22.5%; shop-router (2689.9) wins 48.4%.
Drift test settles it: our own byte-identical resubmissions scored 2383->1809 and 2478->1850.

**PANEL BLIND SPOT, now fixed.** shop-router-v7 was missing from the opponent field entirely, despite
CLAUDE.md recording it as the tetsutani family's 98.1% nemesis. Added it plus pipe-7, v49, v54-productive.
`broad` (339,857 games, 16 lineages): champion **93.7%**, frontier-0923 93.1%, shepherds-0925 85.7%,
masterhybrid 78.8%, guard:shoprouter 53.3%, shoprouter 48.4%, v49 22.5%, utils/v43 3.1%.
The champion is NOT overfitted to relatives -- it scores *higher* on the broad panel than the narrow one.

**But the meta is rock-paper-scissors** (`runs/h2h.py`, direct head-to-head, both seats):
- shop-router beats our champion **92.5%** (6W-74L) and beats masterhybrid 100%, frontier-0923 91.7%
- Herd-Safe lineage (shepherds-0925, dmitrii-2700) beats shop-router **95-100%**
- our champion beats Herd-Safe 77.5% (57.5% guarded)
A single agent cannot cover this; the tracked PAIR can. Submitted 56558912 (Frontier corner) +
56558917 (Herd-Safe corner, guard-baked) as a deliberately cross-lineage pair.

**`runs/opp_id.py` -- what our live opponents actually run** (30 replays, match depth 400 turns;
120 is useless because the lineage shares one tape until the router branches at step 144):
masterhybrid-lineage 16, frontier-0923 7, tetsutani 2, cha22 1, unidentified 4. **shop-router: ZERO.**
So the blind spot is not being exploited live, and 23/30 opponents share OUR lineage.

**The anomaly that reframes everything:** our champion beats the *public* versions of those agents
100/100/100/91.7%, predicting ~99.7% vs the observed mix -- but we win **43% (13/30) live**. Median
first divergence from the public base is **step 150**, right after the router branch. The field is not
running public files; it is running the same base plus their own private layers, exactly like us.
We are mid-crowd among forks of one agent, and our measured edge over the bare base is only ~+2.3pp.

**Hypothesis raised and KILLED before building anything:** HIRE was the top op at divergence points
(96), suggesting winners out-hire the base. Measured (`runs/hire_stats.py`): **275.8 hires/game on both
sides, identical** -- it ranks high only because HIRE is frequent. No wrapper built.

**Where their edge sits** (`opt/live_gap.py`, mean revenue advantage in games we lose): WOOL **+$243**,
CARROT +$95, STRAWBERRY +$82, total ~$420 against a ~$550 median loss margin. No single product
explains it; these are coin flips between near-identical agents.
