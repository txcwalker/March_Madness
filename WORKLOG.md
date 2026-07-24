# WORKLOG.md

Reverse-chronological session ledger. Newest entry on top. Each entry: date, what was done, what's next. Keep entries factual and brief — this is a ledger, not a narrative.

---

## 2026-07-22

Initialized the project. Audited the prior codebase (`../March_Madness_2026`, née `txcwalker/March_Madness_2024` on GitHub) and found it functionally broken: a missing/broken import chain, hardcoded season year and bracket size scattered across files, an undocumented manual Excel step for cleaning KenPom exports, and duplicate `.py`/`.ipynb` implementations that had drifted out of sync. Decided against a full logic rewrite — the modeling/domain logic (KenPom cleanup rules, bracket slot mechanics, conference tiers) is sound and expensive to rederive; only the structure/plumbing needs rebuilding. Agreed on a target repo structure (config-driven season/bracket settings, `src/` as sole production code, notebooks exploration-only, automated KenPom ingest). Created this repo at `March_Madness/`, initialized git, and scaffolded the documentation backbone (`README.md`, `AGENTS.md`, `DEVELOPMENT.md`, `WORKLOG.md`, `GOAL_TRACKER.md`).

**Next:** repo skeleton (`config/`, `src/march_madness/`, `scripts/`, `notebooks/`, `tests/`, `data/`, `reports/`), dependency manifest, and `.gitignore`.

Before committing, defined the full project roadmap with the user. Established one standing priority (audit/cleanup/reorganization/modularity — ongoing, never "done") plus six sequential milestones: (1) port & modularize the existing product at feature parity [current focus], (2) presentation/visualization, (3) seed prediction depth, (4) upset finder & Cinderella stories, (5) sportsbook/prediction market API integration, (6) in-season predictive modeling incl. bubble-team at-large prediction — explicitly a ~2-year-out stretch goal since preseason data alone is weak for this. Updated `README.md` and `GOAL_TRACKER.md` to reflect this structure.

**Next:** review roadmap with user, then commit the documentation backbone and start on Milestone 1 (repo skeleton).

Committed and pushed the documentation backbone to a new public GitHub repo (`txcwalker/March_Madness`) after confirming visibility/name with the user. User asked that pushes to any remote/live repo always get a check-in first, even when the surrounding task was already approved — saved as a standing cross-project preference.

Built the Milestone 1 repo skeleton: `config/`, `src/march_madness/{ingest,features,models,bracket,analysis}` (empty `__init__.py` placeholders), `scripts/`, `notebooks/`, `tests/`, `data/{raw,processed,outputs}`, `reports/`. Added `pyproject.toml` (src-layout, dependencies carried over from the legacy `.venv` plus `pyyaml`) and extended `.gitignore` for packaging artifacts. Nothing has real logic yet — next steps are `config/season.yaml` + loader, then the bracket structure module.

**Next:** confirm with user before committing/pushing the skeleton, then start on `config/season.yaml` schema + `src/march_madness/config.py` loader.

User confirmed the skeleton matches the agreed architecture. Two new requirements surfaced, both elevated to standing priorities in `README.md`/`GOAL_TRACKER.md` alongside the audit/cleanup one: (1) year-over-year reuse is a hard requirement, not just a nice-to-have — `data/{raw,processed,outputs}` need a per-year layout so seasons coexist and `config/season.yaml`'s `year` field is a real toggle, decided alongside the upcoming config module; (2) post-mortem/performance evaluation tooling (comparing predictions to actual results after a tournament) is wanted but explicitly deferred — user wants to co-design it once there's a real season of predictions to evaluate against, not spec it now.

**Next:** build `config/season.yaml` schema + `src/march_madness/config.py` loader, including the per-year data directory convention.

Built and verified the config module: `config/season.yaml` (year + bracket size/rounds/play-in count), `src/march_madness/config.py` (`load_season_config()` returns a validated `SeasonConfig` with `raw_dir`/`processed_dir`/`outputs_dir` derived per-year under `data/<kind>/<year>/`; `ensure_data_dirs()` creates `processed`/`outputs` but deliberately leaves `raw` alone so a missing input dir fails loudly rather than silently). Added `tests/test_config.py` (7 tests) and a `dev` extra (`pytest`) to `pyproject.toml`. Discovered the system default Python was 3.8 — recreated `.venv` against the Python 3.10 install the legacy project used, upgraded pip (old pip couldn't do editable installs from `pyproject.toml` alone), installed the package, ran the full test suite (7/7 pass), and sanity-checked `load_season_config()` against the real `config/season.yaml` with no arguments to confirm the default path resolves correctly. Updated `README.md`, `AGENTS.md`, `DEVELOPMENT.md`, and `GOAL_TRACKER.md` to match.

**Next:** confirm with user before committing/pushing, then start on `src/march_madness/bracket/structure.py` (format-agnostic rounds/slots).

User corrected a wrong assumption before this got built: `R1`...`R6` and the 64-team bracket are Kaggle's fixed data format, not something to abstract away — the sims are designed around it. What's actually variable is the play-in stage; user expects a future 76-team format to use 12 play-in games (vs. 4 today). Inspected the real `MNCAATourneySlots.csv`/`MNCAATourneySeeds.csv` from the legacy project to ground the design in the actual schema rather than assumptions, and derived `field_size = 64 + num_play_in_games` (68=64+4 today, 76=64+12 matches the user's expectation).

That inspection also surfaced a real bug: in the raw Kaggle file, play-in slots (e.g. `X16`) are listed *after* the R1 rows that reference them as a seed. The legacy simulator (`sims_mens.py`) iterates in raw file order with no sort, so it would look up an unresolved play-in winner — a genuine latent bug in the old code, not something to carry forward.

Built `src/march_madness/bracket/structure.py`: fixed R1-R6 round classification/naming (ported from the legacy `round_dict`), `validate_bracket_config()` enforcing the size/play-in-count invariant, `validate_slots()` for checking real season data against config, and `order_slots_for_simulation()` which fixes the play-in ordering bug. Added `tests/test_bracket_structure.py` (14 tests, covering both the current 4-play-in format and a synthetic 12-play-in/76-team scenario) and additionally verified the module directly against the real 2024 `MNCAATourneySlots.csv` from `../March_Madness_2026` — confirms the ordering bug is real and that the fix works on actual data, not just synthetic fixtures. Full suite: 27/27 passing.

Corrected `README.md`, `AGENTS.md`, and `GOAL_TRACKER.md` — they previously said (incorrectly, before this conversation) that hardcoding `R1`..`R6` would be a regression to avoid; fixed to reflect that those are legitimate fixed constants and `num_play_in_games` is the actual config-driven lever.

**Next:** confirm with user before committing/pushing, then start on `ingest/kaggle.py` and `ingest/kenpom.py`.

Built both ingest modules, grounded in real data the same way as `bracket/structure.py`.

`ingest/kaggle.py`: `load_kaggle_data(kaggle_dir)` loads the seven Kaggle CSVs the pipeline actually uses (teams, seeds, slots, regular season/tourney compact results, conferences, team conferences) into a `KaggleData` bundle, with a clear error if a file's missing. Verified against the real, full 2026 Kaggle data directory from the legacy project (198K+ regular season game rows, etc.) — loads cleanly.

`ingest/kenpom.py`: `clean_kenpom_export()` drops rank-subscript/blank columns, drops stray repeated header rows, splits Team/Seed and W/L apart, adds a Season column. `build_kenpom_history()` scans `data/raw/*/kenpom_raw.csv` and merges every available year — the automated replacement for re-pasting the full history by hand each season. Verified against the real `kenpom_2026_raw.csv` (365 teams) and found a real bug in the process: Excel silently reformats a `W-L` value like `20-12` into the date `20-Dec` whenever the loss count looks like a month number, corrupting ~90 of 365 teams' (25%) loss counts on every paste. Fixed by recovering the loss count from the month abbreviation. This had apparently been happening unnoticed. Deliberately did not reconcile KenPom team names to Kaggle `TeamID`s here (KenPom's names don't match Kaggle's `TeamID`-keyed names) — that belongs in `features/build_features.py`, next up.

40 tests total (was 27; +3 kaggle, +10 kenpom including the Excel bug case), all passing. Docs updated (README.md, AGENTS.md, GOAL_TRACKER.md).

**Next:** confirm with user before committing/pushing, then start on `features/build_features.py` (matchup pairing, conference tiers, and the KenPom-to-TeamID reconciliation deferred from ingest).

Built `features/build_features.py`, grounded in the legacy `ncaabwinsmodel.py`'s matchup-construction logic (read the real code rather than guessing). Two significant real-data findings, both fixed:

1. **Team-name matching**: an exact `Team` == `TeamName` match (what the legacy project did) matched only 228/365 real 2026 teams (62%) — KenPom's "Iowa St." never equals Kaggle's "Iowa State", etc. Kaggle ships `MTeamSpellings.csv` specifically for this; using it instead recovered 352/365 (96%). Added `team_spellings` to `ingest/kaggle.py`'s `KaggleData`/`_FILES` (this required going back and editing the already-committed ingest module). `match_kenpom_teams()` now returns both matched and unmatched rows, so the remaining ~4% stays visible instead of silently disappearing like before.

2. **Positional alignment bug**: the legacy tournament-game merge joined winner-rows to loser-rows by row position, not a real key — if either side's join with KenPom stats dropped a different row, this would silently pair unrelated games together. `build_matchup_history()` joins on an explicit `GameID` instead. Added a regression test that constructs exactly this scenario (one team missing KenPom data) and confirms the game is dropped cleanly rather than misaligned.

Also found, while verifying against real data: KenPom's conference abbreviations drift over time just like `AdjEM`→`NetRtg` did — the legacy `conf_mapping` used `Pat` for the Patriot League, but the real 2026 export uses `PL`, and was also missing `BW`/`SC`/`BSth` entirely. Without these, 10% of real matchup rows got a silently null conference; fixed by adding the missing/current abbreviations to `KENPOM_TO_KAGGLE_CONFERENCE`. Re-verified: 0 null conferences on the real 5,265-row 2026 matchup history.

Also ported `random_id`/`stat_swap` as `randomize_matchup_sides()` — vectorized instead of the legacy per-row Python loop (same behavior, meaningfully faster on the full multi-decade game history), and consolidated `conf_mapping`/`conference_tiers`, which existed as two inconsistent copies across `ncaabwinsmodel.py` and `seed_prediction.py` in the legacy project, into one canonical version.

49 tests total (was 40; +9 in test_build_features.py), all passing. Verified end-to-end against real 2026 Kaggle + KenPom data. Docs updated (README.md, AGENTS.md, GOAL_TRACKER.md).

**Next:** confirm with user before committing/pushing, then start on `models/` (logistic regression, random forest, XGBoost, neural net, seed KNN).

Built all five models in one pass, grounded in the four legacy model scripts (`ncaabwins_logreg.py`, `ncaabwins_randomforest.py`, `ncaabwins_nn.py`, `ncaawins_xg.py`) plus `seed_prediction.py`. All four legacy win-probability scripts duplicated the same split/scale/fit/evaluate boilerplate almost verbatim, with small inconsistent variations (different train/test ratios per model, two different ECE formulas, ~150-250 lines of near-identical plotting code each). Consolidated into `models/common.py` (`prepare_model_matrix`, `split_features`, `evaluate_classifier`, `train_and_evaluate`) shared by all four; each model file now only exposes `build_model()`. Deliberately left plotting out entirely — that's Milestone 2's job, not modeling's.

Design decisions along the way:
- `prepare_model_matrix()` explicitly excludes `Score_A/B` (the actual game score — leakage, unknown before the game happens) and `Seed_A/B` (null for ~80% of matchup rows, since only tournament teams ever have one) from the feature set. The legacy code already dropped scores for the same reason; this makes it an explicit, documented, tested exclusion rather than an implicit one.
- Conference is encoded via `conference_tier()` (reusing `build_features.py`) rather than a fresh `LabelEncoder`, avoiding the false ordinality an arbitrary integer-coded categorical implies to a linear/distance-based model.
- Tree-based models (`random_forest`, `xgboost_model`) are bare estimators, not scaler pipelines — scaling is mathematically a no-op for decision tree splits, so the legacy code's blanket scaling of every model was harmless but pointless for these two.
- Fixed a real breakage: the legacy XGBoost script passed `use_label_encoder=False`, a parameter removed entirely from modern `xgboost` (raises `TypeError` if passed). Not carried forward.
- `seed_knn.py` is structurally separate — trains on one row per team-*season* (only teams with a known seed), not per matchup. Evaluates with mean absolute seed error alongside accuracy, since seed is ordinal and a miss-by-1 is very different from a miss-by-14.

Verified all five against real 2026 data end-to-end (5,265 real games for the four classifiers; the real 68 seeded teams for seed_knn) rather than only synthetic fixtures:

| Model | Accuracy | ROC-AUC | Log Loss | Brier |
|---|---|---|---|---|
| Logistic Regression | 74.5% | 0.837 | 0.489 | 0.164 |
| Random Forest | 70.6% | 0.769 | 0.627 | 0.201 |
| XGBoost | 68.1% | 0.769 | 0.665 | 0.220 |
| Neural Net | 70.1% | 0.790 | 0.564 | 0.192 |

Logistic regression currently performs best — plausible, since win probability from KenPom efficiency-margin differential is close to genuinely logistic. `seed_knn` works end-to-end (best_k=1, mean absolute seed error 1.48) but is data-starved: this repo only has one real season (2026, 68 seeded teams) to train on, ~4 examples per seed class. Flagged in AGENTS.md as an expected limitation, not a bug — it improves automatically as more years' raw KenPom pastes accumulate under `data/raw/<year>/`.

60 tests total (was 49; +11 in test_models.py), all passing. Docs updated (README.md, AGENTS.md, GOAL_TRACKER.md).

**Next:** confirm with user before committing/pushing, then start on `bracket/simulate.py` (Milestone 1's last remaining piece besides porting seed clustering/round-count analysis).

Built `bracket/simulate.py`, grounded in the legacy `sims_mens.py`'s `simulate()`/`run_simulation()`/`prep_data_sim()`. The legacy version relied on a numpy 2D-array-broadcasting quirk to make `probs_dict[team1][team2]` hold a 2-element array (from `predict_proba` returning shape `(1,2)` and `1 - probs[0]` broadcasting) rather than a plain float — worked, but the intent wasn't visible from reading the code. Rewrote as plain scalar probabilities throughout. Kept the legacy design where the same dict serves as both a seed-code lookup and a slot-code (resolved winner) lookup during simulation — it's genuinely elegant and the two namespaces never collide.

Added `build_prediction_matrix()` to `models/common.py` as the inference-time mirror of `prepare_model_matrix()` — turns a hypothetical (team1, team2) pair into the same feature shape a trained model expects, using the same `STAT_COLUMNS`/`conference_tier()` as training. `compute_win_probabilities()` prices every matchup in the field once, up front, rather than calling the model mid-simulation for every game of every bracket.

11 new tests (7 for `bracket/simulate.py`, using a small synthetic 4-team bracket with extreme win probabilities so outcomes are deterministic even in "stochastic" mode -- `rng.random() < 1.0` is always true). 67 tests total, all passing.

Ran a full real end-to-end simulation on the actual 2026 bracket (2,000 Monte Carlo brackets, logistic regression trained on the real 5,265-game history) and found two more real data quirks along the way:

- **2026's `MNCAATourneySeeds.csv`/`MNCAATourneySlots.csv` has zero play-in rows** (64 seeds, 63 slots) — First Four already resolved into a clean field, unlike 2024's data (68 seeds, 67 slots including 4 play-in games). Confirmed by direct comparison. Used a season-specific `BracketConfig(num_play_in_games=0)` for this run rather than assuming `config/season.yaml`'s default applies to every season's raw file.
- **One real 2026 tournament team, "Queens NC" (seed Z15), has no `MTeamSpellings.csv` entry** — part of the already-known ~4% match gap from the feature-building work, now identified concretely rather than just as a percentage. Substituted average stats across matched teams for this one run, clearly logged as a substitution, not silently absorbed.

The simulation's results are a strong real-world sanity check on the whole pipeline built this session: top simulated champions (Duke 33.2%, Michigan 23.9%, Arizona 17.9%) are exactly the top 3 teams by real KenPom rating from the start of this session — config, bracket structure, ingest, features, models, and simulation are all correctly wired together end-to-end on real data.

**Next:** confirm with user before committing/pushing, then start on `analysis/` (region strength, upsets, round-advancement counts) and porting `seed_clustering.py` -- the last pieces of Milestone 1's port.
