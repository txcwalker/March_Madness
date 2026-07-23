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
