# GOAL_TRACKER.md

Status legend: `done` | `in-progress` | `pending` | `modified` | `superseded`

| Item | Status | Target |
|---|---|---|
| Standing: Audit / Cleanup / Reorg / Modularity | in-progress | ongoing |
| Standing: Year-over-Year Reuse | pending | ongoing |
| — `run_pipeline.py` default model, final state 2026-07-30: `xgboost_model`. History: logistic_regression → xgboost_model (accuracy 0.681, looked broken) → reverted → root-caused to training-data starvation → historical KenPom backfill → xgboost_model 0.744 vs logistic_regression's 0.755, close enough that the user chose xgboost_model as live default | done | 2026-07-30 |
| — **Found and fixed a real simulation bug, not a model problem**: after the backfill, Duke's title share was still implausible (67.5%) despite near-identical KenPom ratings to Arizona/Michigan. Traced to `bracket/simulate.py`'s `compute_win_probabilities()`: the fitted model is not slot-invariant (same real matchup gave 64%/38% one way, ~38%/62% reversed, depending on which team's stats sat in the "_A" feature slot vs "_B"), and `simulate_bracket` always placed the bracket's StrongSeed in the same slot, compounding an unearned edge every round. Fixed by symmetrizing (`probs[a][b] + probs[b][a] == 1.0`, always). Duke's title share dropped 67.5%→41.0% with nothing else changed; new test added (`test_compute_win_probabilities_symmetrizes_away_a_slot_position_bias`) | done | 2026-07-30 |
| — `scripts/evaluate_models.py` + `reports/model_calibration.png` — trains all 4 candidate models on an identical split, prints a metrics table (incl. expected calibration error, which `models/common.py` computed but `run_pipeline.py` never printed), and plots a real reliability diagram | done | 2026-07-30 |
| — **Historical KenPom backfill** — real root cause of the RF/XGBoost/NN accuracy gap vs. the legacy project: rebuild was training on 1 season (2026, 5,265 games) vs. legacy's 23 seasons (2003-2025, ~120,000 games). `scripts/backfill_historical_kenpom.py` imports the legacy project's already-merged `kenpom_fin_df.csv` into `data/processed/<year>/kenpom_clean.csv`; `ingest/kenpom.py`'s `build_kenpom_history()` now also picks those up (raw export still preferred when both exist for a year). After backfill: xgboost_model accuracy 0.681→0.744, ECE 0.145→0.024; neural_net accuracy 0.701→0.753, ECE 0.077→0.007 (now the best-calibrated model). Deliberately did NOT bring back legacy's `TeamID_A`/`TeamID_B` features — those were a real identity-leakage bug in the legacy code (row-random split let a team's ID leak across train/test) that inflated its old RF/XGBoost/NN numbers; user agrees to leave them out for now but flagged real, non-leaky reasons a team/program-identity feature might be legitimate signal in the NIL/transfer-portal era (see WORKLOG) — worth deliberate testing in Milestone 3, not a default inclusion | done | 2026-07-30 |
| — Found and fixed a second, previously-unknown variant of the Excel W-L date-mangling bug while backfilling: the known fix only recovered a mangled **loss** count (e.g. "20-12"→"20-Dec"); real historical data (Alcorn St. 2010, Binghamton 2012) also had mangled **win** counts (e.g. "2-29"→"Feb-29"), which silently produced `NaN` and crashed model training. `parse_win_loss_component()` (renamed from `parse_losses`) now applies to both sides; 2 real rows fixed, tests added | done | 2026-07-30 |
| Documentation backbone | done | 2026-07-22 |
| Git repository initialized | done | 2026-07-22 |
| **Milestone 1: Port & Modularize Existing Product** | **done** | **2026-07-22** |
| — Dependency manifest (pyproject.toml) | done | 2026-07-22 |
| — .gitignore | done | 2026-07-22 |
| — Repo skeleton (config/, src/, scripts/, notebooks/, tests/, data/, reports/) | done | 2026-07-22 |
| — config/season.yaml schema (incl. per-year data layout) | done | 2026-07-22 |
| — Config loader (src/march_madness/config.py) | done | 2026-07-22 |
| — Bracket structure module (play-in-count-agnostic; R1-R6/64 fixed) | done | 2026-07-22 |
| — Kaggle ingest module | done | 2026-07-22 |
| — KenPom ingest automation | done | 2026-07-22 |
| — Feature engineering module | done | 2026-07-22 |
| — Logistic regression model | done | 2026-07-22 |
| — Random forest model | done | 2026-07-22 |
| — XGBoost model | done | 2026-07-22 |
| — Neural net model | done | 2026-07-22 |
| — Seed KNN model | done | 2026-07-22 |
| — Bracket Monte Carlo simulator | done | 2026-07-22 |
| — Seed clustering + round-count/fragility analysis | done | 2026-07-22 |
| — Pipeline entry point (scripts/run_pipeline.py) | done | 2026-07-22 |
| **Milestone 2: Presentation & Visualization** | **in-progress** | **TBD** |
| — ~~Site architecture: Jinja2 + Markdown static site~~ | superseded | 2026-07-27 |
| — ~~Six analytics pages built on Jinja2 (Round Odds, Over/Underperformers, Cinderella, Final Four Finder, Region Strength, Seed Prediction)~~ | superseded | 2026-07-27 |
| — ~~GitHub Pages hosting~~ | superseded | 2026-07-27 |
| — Superseded Jinja2 build moved to `legacy/jinja_site/` (content/, site/, docs/, build_site.py) | done | 2026-07-28 |
| — jinja2/markdown deps removed from pyproject.toml | done | 2026-07-28 |
| — Site architecture: Vite + React, glassmorphism system from `NFL_Exploration`/`CaravanserAI` (dark/blur/glow, blue+orange, hand-written CSS, no Tailwind) | done | 2026-07-27 |
| — Visual design direction: Minimal Editorial, both light and dark themes designed | done | 2026-07-28 |
| — Hosting: local only for now, matching NFL_Exploration/CaravanserAI (neither is publicly deployed yet) | done | 2026-07-28 |
| — `frontend/` scaffold (Vite + React, port 5181, mirroring NFL_Exploration/frontend structure — no router, pagesConfig.js pattern) | done | 2026-07-28 |
| — `scripts/export_site_data.py` — JSON data hand-off (resolves the JSON-vs-CSV decision: pipeline output → JSON, not the frontend parsing CSV) | done | 2026-07-28 |
| — Home / executive-summary page (stat strip, region outlook, Final Four + odds teasers) | done | 2026-07-28 |
| — Round Odds page (React, all teams, sortable columns) | done | 2026-07-28 |
| — Over/Underperformers page (React, sortable table + diverging bar chart of biggest over/underperformers) | done | 2026-07-30 |
| — Cinderella Watch page (React, seed-threshold x round heatmap) | done | 2026-07-30 |
| — Final Four Finder page (React — four region dropdowns for a partial-or-full team selection, bar chart + list of matching Final Fours, exports the full ~266-combo list rather than a top-N slice so any selection is answered honestly, incl. "never occurred") | done | 2026-07-30 |
| — Region Strength audited and fixed: primary fragility stat switched from "top seed's share of this region's outright titles" (conditioned on the region winning it all — conflated cross-region strength and was statistically unstable, e.g. one region's figure came from ~120 of 10,000 brackets) to "top seed's share of this region's Final Four appearances" (unconditional, all 10,000 brackets). Added `region_top_seed_final_four_share()` + test; old metric kept as a secondary stat, not deleted. Home + Region Strength pages updated; Region Strength page now also has a championship-share bar chart | done | 2026-07-30 |
| — Home page: championship-odds bar chart added alongside the table | done | 2026-07-30 |
| — `components/SortableTable.jsx` extracted (shared by Round Odds and Over/Underperformers) | done | 2026-07-30 |
| — Fixed a real bug in `export_site_data.py`: a team that never wins a single simulated game (e.g. Furman, Prairie View under xgboost_model's more confident predictions) was silently dropped from the whole export instead of showing at ~0% — same class of bug `average_wins_by_team()` already guards against in `analysis/round_advancement.py`. Team payload now anchors on the full `teams.csv`, not on whichever teams happened to win a game | done | 2026-07-30 |
| — Seed Prediction page — deliberately deferred, not scoped yet: user has learned more about clustering since the original design and wants to redo it before it goes live, target before the 2027 season publish | pending | before 2027 publish |
| Milestone 3: Seed Prediction (depth beyond KNN baseline) | pending | TBD |
| Milestone 4: Upset Finder & Cinderella Stories | pending | TBD |
| **Milestone 5: Bracket Path & Historical Tools** *(new)* | pending | TBD |
| — Path of Least Resistance (which team has the weakest path to the Final Four) | pending | TBD |
| — Who Benefits if Team X Loses (separate from Path of Least Resistance) | pending | TBD |
| — Post-Mortem / Year Retrospective (design TBD with user — moved here from Milestone 2) | pending | TBD |
| — Previous-Years History (side-by-side multi-season view) | pending | TBD |
| Milestone 6: Sportsbook & Prediction Market Integration | pending | TBD |
| Milestone 7: In-Season Predictive Modeling (bubble teams) | pending | ~2 years out |
| Women's tournament support | pending | TBD |
| 76-team format validation | pending | TBD |
