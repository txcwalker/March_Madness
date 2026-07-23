# WORKLOG.md

Reverse-chronological session ledger. Newest entry on top. Each entry: date, what was done, what's next. Keep entries factual and brief — this is a ledger, not a narrative.

---

## 2026-07-22

Initialized the project. Audited the prior codebase (`../March_Madness_2026`, née `txcwalker/March_Madness_2024` on GitHub) and found it functionally broken: a missing/broken import chain, hardcoded season year and bracket size scattered across files, an undocumented manual Excel step for cleaning KenPom exports, and duplicate `.py`/`.ipynb` implementations that had drifted out of sync. Decided against a full logic rewrite — the modeling/domain logic (KenPom cleanup rules, bracket slot mechanics, conference tiers) is sound and expensive to rederive; only the structure/plumbing needs rebuilding. Agreed on a target repo structure (config-driven season/bracket settings, `src/` as sole production code, notebooks exploration-only, automated KenPom ingest). Created this repo at `March_Madness/`, initialized git, and scaffolded the documentation backbone (`README.md`, `AGENTS.md`, `DEVELOPMENT.md`, `WORKLOG.md`, `GOAL_TRACKER.md`).

**Next:** repo skeleton (`config/`, `src/march_madness/`, `scripts/`, `notebooks/`, `tests/`, `data/`, `reports/`), dependency manifest, and `.gitignore`.

Before committing, defined the full project roadmap with the user. Established one standing priority (audit/cleanup/reorganization/modularity — ongoing, never "done") plus six sequential milestones: (1) port & modularize the existing product at feature parity [current focus], (2) presentation/visualization, (3) seed prediction depth, (4) upset finder & Cinderella stories, (5) sportsbook/prediction market API integration, (6) in-season predictive modeling incl. bubble-team at-large prediction — explicitly a ~2-year-out stretch goal since preseason data alone is weak for this. Updated `README.md` and `GOAL_TRACKER.md` to reflect this structure.

**Next:** review roadmap with user, then commit the documentation backbone and start on Milestone 1 (repo skeleton).
