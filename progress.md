# Kaggriculture — progress and handoff

**Last updated: 2026-09-26.** Read `CLAUDE.md` first (engine facts, hard constraints, the daily
ritual), then this file. `PLAN.md` is the dated experiment log — this file is the *current* state.

Competition ends **2026-09-30**. 5 submissions/day. Only the **latest 2** submissions count for the
final Bradley-Terry leaderboard, and a new submission evicts the older of the two.

**Submit only from ISHRAQ** (`farhanishraqq`). Submitting the same agent from teammate accounts is
multi-account abuse and disqualifies the team.

---

## 1. TL;DR for whoever picks this up

- We ride the **best public agent** and add two small, measured wrappers of our own. We do not have
  our own competitive agent from scratch — that was tried and failed by 6×.
- Current live pair: **56558912** (Frontier + guard + milk-skip) and **56558917** (Shepherd's
  Herd-Safe + guard) — deliberately two *different lineages*, because the meta is rock-paper-scissors.
- **Every wrapper/meta lever we could think of is now measured and closed** (section 5). The two that
  paid are shipped. Do not re-run the sweeps in section 6 without a new hypothesis.
- The single most useful ongoing activity is the **daily Code-tab survey** (CLAUDE.md) — the best
  available base changed three days running, and swapping base was worth ~15pp where our wrappers
  are worth ~2pp.
- **Ratings drift down hard.** Never compare numbers from different days (section 3).

---

## 2. Live submissions, newest first

| Sub ID | Date | Agent | Live |
|---|---|---|---|
| **56558917** | 09-25 | **PAIR 2/2** Shepherd's Herd-Safe-0925 + guard 14 | 2029.7 |
| **56558912** | 09-25 | **PAIR 1/2** Frontier-0923 + guard 14 + skip-milk | 2016.2 |
| 56557488 | 09-25 | drift test: byte-identical to the file that scored 2478.5 | **1970.3** |
| 56557484 | 09-25 | drift test: byte-identical to the file that scored 2383.0 | **1779.1** |
| 56555247 | 09-25 | Frontier-0923 + guard + milk-skip (first milk build) | 2023.6 |
| 56532146 | 09-24 | Frontier-0923 unmodified (guard control) | 2084.3 |
| 56508972 | 09-24 | Frontier-0923 + guard 14 | 2180.3 |
| 56502435 | 09-23 | Frontier-0922 unmodified | 2383.0 |
| 56497677 | 09-23 | tetsutani-0921 resubmitted (same bytes as the 2583.1 file) | 2193.6 |
| 56470642 | 09-22 | dmitriigluzdov Herd-Safe | 2478.5 |
| 56442774 | 09-21 | tetsutani-0921 unmodified | **2583.1** (best ever) |
| 56406154 | 09-20 | public fork-2801 | 1934.8 |
| 56406056 / 56405251 | 09-20 | our own from-scratch policies | 495 / 434 |

---

## 3. Ratings drift — the single most important measurement discipline

The same bytes, resubmitted later, score far lower. Measured three times:

| File | Original | Resubmitted | Drop |
|---|---|---|---|
| tetsutani-0921 (sha `9c0a8921`) | 2583.1 (09-21) | 2192.5 (09-23) | −391 |
| dmitrii Herd-Safe (sha `4889137f`) | 2478.5 (09-24) | **1970.3** (09-25) | −508 |
| Frontier-0922 (sha `bc80b476`) | 2383.0 (09-23) | **1779.1** (09-25) | −604 |

Corroborated independently by destbreso's `ladder_forecast.json` (`data/bench/`): a fixed submission's
median rating decays 2087 → 1738 as it plays more episodes.

Consequences:
- **Never compare ratings from different days.** Compare agents at the same age, or not at all.
- Notebook score badges are **frozen at submission time**. `v43-local-confirmed` shows 2550.5 and is
  byte-identical to a file that wins **3.1%** against today's field; v49 shows 2467.0 and wins 22.5%;
  shop-router shows 2689.9 and wins 48.4%. Do not chase badges.
- "2583 was our best, we're falling" is wrong — that number is unreachable now by any agent.

---

## 4. What the live field actually is (`runs/opp_id.py`)

Replays our own live games with candidate agents in the opponent's seat and measures how many turns
match. **Match depth must exceed 400** — the public lineage shares one tape until the router branches
at step 144, so a 120-turn match proves nothing.

Over 30 live replays: **masterhybrid-lineage 16, frontier-0923 7, tetsutani 2, cha22 1, unidentified 4,
shop-router 0.**

**23 of 30 opponents are our own lineage**, diverging at a median of step 150 — right after the router
branch. They are not running the public files; they run the same base plus their own private layers,
exactly like us. Our champion beats the *public* versions of those agents 100/100/100/91.7%, which
predicts ~99.7%, yet we win **43% (13/30)** live. Their private layers are worth about as much as ours.

We are mid-crowd among forks of one agent. Our measured edge over the bare base is ~+2.3pp.

---

## 5. The meta is rock-paper-scissors (`runs/h2h.py`)

Direct head-to-head, both seats:

| | beats | at |
|---|---|---|
| shop-router-v7 | our Frontier champion | **92.5%** (6W-74L) |
| shop-router-v7 | masterhybrid / tetsutani / frontier-0923 | 100% / 100% / 91.7% |
| Herd-Safe (shepherds-0925, dmitrii-2700) | shop-router-v7 | **95–100%** |
| our Frontier champion | Herd-Safe | 77.5% (57.5% vs guarded) |
| our champion | cha22 | 91.7% |
| cha22 | shop-router | 100% |

No single agent covers this cycle; **the tracked pair can**. That is why the two live submissions are
deliberately from different lineages. Most competitors submit two agents of the same family and get
swept by whichever counter appears.

Caveat: shop-router does **not** appear in our live opponent sample, so this insurance may never be
needed — but it costs nothing, since the Herd-Safe build is strong in its own right.

---

## 6. Everything tried

### Shipped and paying

| Change | Evidence |
|---|---|
| **Shed-overflow guard, margin 14** (`opt/shed_guard.py`) | **+1.72pp, z=18.78, 98,671 paired games**, pooled over 5 farm + 4 local samples |
| **Never sell MILK** (`--skip MILK`) | **+0.64pp, z=9.47, 181,478 fresh-seed games** (+0.73pp z=11.50 pooled, 204,673) |

Milk works because milk hits the $1 floor after ~76 units and never recovers, so spending it to clear
the 100-item shed cap destroys more value than bulk does. **Item-specific**: skipping STRAWBERRY is
−1.84pp, wool +0.14 (ns), melon 0.00 (never fires).

### Closed — measured negatives, do not retry without a new hypothesis

| Lever | Result |
|---|---|
| Guard knobs: margins 11–22, price floors p5–p30, item skips, combinations | 129k + 199k games, everything within ±0.22pp of shipped; margin 14 + skip-milk is a local optimum |
| Cheap-first sell ordering (`:L`) | −1.89pp (z=−14.61), worse at higher margins, 153,359 games |
| Sale-advance / opponent-dump forecast (`opt/sale_advance.py`) | −2.9 to −28.8pp, monotonically worse with more lead |
| Idle-worker layer (`opt/idle_work.py`) | CARE fires once/game, fertilizer +$7/game — units are parked on watered plants and empty pastures |
| **Wheat speculation** (`opt/trader.py`) | Never fires safely (base already has a wheat order on 218 turns/game); forced, **8.3% vs 100%** |
| Cross-family routing | Oracle +5.2pp but **unreachable**: candidates diverge at step 0, so there is nothing to condition on |
| Fertilizer cutoff f684 | +1.03pp on the old tetsutani base, **0.00 on Frontier** |
| Our own policy from scratch | Plateaued ~6× behind public agents; live 434–495 |
| tetsutani 2-knob tuning | +1.95pp on that base — but that base is now bottom of the field |
| Round-2 tetsutani knob sweep (12 constants) | 123k games, nothing significant |
| Time-based seed cutoffs | −7 to −55pp (Herd-Safe authors do it *need-based* and report a win — the idea is fine, our implementation was not) |
| Hire-rate hypothesis | Killed before building: 275.8 hires/game on **both** sides |
| Shop steering ("God's mode") | Directed control only 10–18%, impact unmeasured. Parked |

### Never converted, worth knowing

Guard gains are **base-dependent**: +27.5pp on cha22, +20.9pp on evgen, +12.1pp on pop-robust,
+4.0pp on harvest-ledger, but only +1.2–1.7pp on Frontier, which already liquidates well.
`runs/discard_probe.py` predicts this on strong bases (Frontier leaks 5.5 units/game) but **not** on
weak ones (icefire leaks 1.0 yet gained +10.4pp) — use it as a filter, not a veto.

---

## 7. Agent ranking (farm `broad`, 339,857 games, 16 lineages, 2026-09-26)

| Agent | Win % |
|---|---|
| **guard:c-frontier-0923:14:sMILK (ours)** | **93.7%** |
| c-frontier-0923 | 93.1% |
| c-shepherds-0925 | 85.7% |
| c-masterhybrid-2965 | 78.8% |
| guard:c-shoprouter-v7:14 | 53.3% |
| c-shoprouter-v7 | 48.4% |
| c-v49 | 22.5% |
| c-utils-v1 = v43-local-confirmed | 3.1% |

The champion scores *higher* on the broad 16-lineage panel than on the old narrow one, so it is not
overfitted to relatives.

---

## 8. Methodology rules, each learned the hard way

1. **The opponent field must be fixed and disjoint from the candidate list.** Including a candidate's
   own base as an opponent credits it for beating its own mirror: it turned a true +2.48pp into a
   reported +4.34pp, and inflated two other results to +22pp and +29pp.
2. **Anything under ~2k paired cells is unmeasured.** Sign flips observed repeatedly: guard read
   −2.42pp at n=496 and +1.21pp at n=912; a complement read **+4.00pp (z=3.03) at n=375** and settled
   at **−3.50pp over 88k games**. Every large farm sample agreed; only small ones disagreed.
3. **A delta of exactly 0.00 means your layer is not running.** Market orders are **lists**
   `["SELL", item, qty]`; `_parse_order` returns None for any other shape and drops the order
   **silently**. Dict-shaped orders produced 0.00 deltas across 8 variants and 8,320 games.
4. **Discovery and confirmation must use different seed ranges.** Everything shipped was confirmed on
   a fresh block first.
5. **Never judge a build by $-vs-starter.** harvest-ledger-0925 posted $198,166, the highest ever
   measured, and lost to us by 12.4pp over 162,374 games.
6. **Hash-dedupe before testing.** Four notebooks have shipped one identical file (`127ed3e6`).
7. On Windows, `pathlib.write_text()` without `encoding="utf-8"` corrupts source files.

---

## 9. Compute

**8 Kaggle accounts × 5 concurrent CPU sessions = 40 kernels** (ISHRAQ, DIDHITI, TASHIN, SALAM, Eshad,
Mashrafi, Samin, Nasif), tokens in `Secrets.env` (gitignored — never commit it). Plus ~20 local cores,
though the 1 MB public agents run ~700 ms/game, so local yields only a few games/s.

```bash
python scripts/panel_dataset.py                  # push opponents/ to every account first
python scripts/kfarm.py worldeval <min> 5 <seed_base> "<cands>" "<opps>" <tag>
KAGRI_ACCOUNTS=Nasif python scripts/kfarm.py worldeval ...   # pin to accounts with free slots
python runs/wait_tags.py <tag>                   # poll to completion, then harvest
python scripts/kfarm.py harvest_we <tag>         # -> runs/<tag>_all.jsonl
python opt/paired.py "<champion>" runs/<tag>_all.jsonl [more.jsonl] [--only SUBSTR]
```

A 40-shard × 120-minute run yields roughly 150–300k games. The 5-session cap is per account; a 6th
push errors, and `runs/wait_tags.py` ignores shards that failed to launch (otherwise it polls forever).

---

## 10. Tooling

```
engine/fastsim.py          fast engine, parity-verified   engine/test_parity.py  THE GATE
opt/opponents.py           agent loader + runtime variant naming (below)
opt/worldeval.py           paired evaluation              opt/paired.py   deltas + z from jsonl
opt/shed_guard.py          SHIPPED wrapper                opt/sale_advance.py  measured negative
opt/idle_work.py           measured negative              opt/trader.py        measured negative
opt/leftover.py            unsold value at season end     opt/live_gap.py      per-product loss gap
scripts/kfarm.py           the farm       scripts/panel_dataset.py  panel upload
scripts/bake_guard.py      ship the guard (--skip supported)   scripts/bake_variant.py  knob baking
scripts/build_submission.py  validate() = official runner gate
runs/fetch_out.py          pull exact submitted files     runs/smoke.py    load + 1 game
runs/discard_probe.py      shed-leak screen               runs/waste_probe.py  escapes / missed CARE
runs/idle_probe.py         idle labour                    runs/divergence.py   router feasibility
runs/h2h.py                direct head-to-head            runs/opp_id.py   identify live opponents
runs/steal.py              what live winners do differently    runs/hire_stats.py
runs/verify_bake.py        baked file == evaluated variant     runs/livediag.py  pull our replays
```

**Runtime agent naming** (evaluate any combination without writing a file):
- `name@KNOB=VALUE` — rewrite a top-level constant (must match exactly one line)
- `guard:BASE:MARGIN[:opts]` — shed guard; opts joined with `+`: `h`hour_min, `w`wheat_keep,
  `s`ITEM (skip), `c`seed_cutoff, `f`fert_cutoff, `p`min_price, `L` cheap-first
- `idle:BASE[:c+f+w]`, `adv:BASE:LEAD:MINEVENTS[:opts]`, `trade:BASE[:opts]` — the measured negatives
- They stack: `trade:guard:c-frontier-0923:14:sMILK:b32+m40`

**Champion name:** `guard:c-frontier-0923:14:sMILK`

---

## 11. Submission procedure

```python
kfarm.kag("ISHRAQ", token, "competitions", "submit", "-c", "kaggriculture", "-f", path, "-m", msg)
```

Gates for anything we modified, in order:
1. `python scripts/bake_guard.py <base> <margin> [--skip MILK] --out runs/<name>/main.py`
2. `python runs/verify_bake.py` — baked file must reproduce the evaluated variant **to the coin**
3. `build_submission.validate(path)` — official runner, 720 steps, DONE/DONE, worst case < 200 ms
4. Attribution: public agents are Apache-2.0. Keep every upstream notice, name the authors in the
   description. **Never strip authorship.** The shipped builds carry 31–34 notices.

Latency note: the Frontier base measures ~180–190 ms worst case on a loaded machine (Kaggle's limit is
1000 ms). That is the base, not our layers — earlier 45 ms readings were the unrepresentative ones.

---

## 12. State at handoff, and what to do next

**Running:** farm job `pairfinal` (40 kernels, seeds 6.0M) measuring both submitted pair members plus
dmitrii on the broad 16-lineage panel. Harvest with `python runs/wait_tags.py pairfinal`, then
`python opt/paired.py "guard:c-frontier-0923:14:sMILK" runs/pairfinal_all.jsonl`. Use it to decide the
final pair.

**Do this daily** (see CLAUDE.md "DAILY RITUAL"): survey the Code tab, pull exact submitted files,
hash-dedupe, smoke-test, discard-probe, then a farm round-robin against the fixed broad field. Base
selection is the only lever with proven returns.

**On 09-30 (deadline day):** submit the two strongest agents **last**, and as late as practical, so
they are rated in the final field rather than decaying for days first. Keep them cross-lineage.

**Honest assessment.** Our champion beats every public agent we can find (93.7% over 339k games), but
the live field is other people's forks of the same base, and we win 43% of those. Our edge over the
bare base is ~+2.3pp. Reaching the prize cutoff would need something categorically better than
"best public base + small wrappers", and every wrapper-shaped idea we could construct is in section 6
with a number next to it. The remaining honest leads, neither of which we pursued to completion:
- **Wool / YARN_STORE composition** — the largest single revenue gap in live losses ($243/game,
  vs carrot $95 and strawberry $82, against a ~$550 median loss margin). It is shop-driven, so it is
  reactive territory a wrapper could in principle reach.
- **Need-based late-purchase limits** as the Herd-Safe authors implement them (ours was time-based and
  failed at −7 to −55pp).
