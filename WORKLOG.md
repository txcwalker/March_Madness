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
