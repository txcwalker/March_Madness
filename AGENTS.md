# AGENTS.md

AI-to-AI handoff contract. Keep this current and terse — dense facts, no prose padding.

## Core Purpose

Rebuild of a March Madness bracket prediction/simulation project. Ground-up restructure of a working-but-tangled prior codebase (see Frozen/Legacy Zones). Goal: config-driven, format-agnostic, reusable every season without hand-editing.

## Current Priorities

1. Repo skeleton + `pyproject.toml` (not yet created)
2. `config/season.yaml` + loader
3. `bracket/structure.py` (config-driven rounds/slots — see Fragile Areas)
4. `ingest/kenpom.py` (automates the header-row/rank-column cleanup described below)

Nothing beyond documentation exists in this repo yet. Do not assume any module below is implemented until it appears in Active Files.

## Active Files

None yet — documentation only (this file, `README.md`, `DEVELOPMENT.md`, `WORKLOG.md`, `GOAL_TRACKER.md`).

## Frozen / Legacy Zones

- `../March_Madness_2026/` (sibling folder, outside this repo) — the prior implementation. **Read-only reference, never import from it or copy it wholesale.** Pull specific working logic in deliberately (feature engineering, KenPom parsing quirks, bracket slot mechanics, conference tier mapping) and rewrite it into this repo's structure.
- Known issues in that legacy code — do not reintroduce them here: broken import chain (`sims_mens.py` imports a name `seed_prediction.py` no longer defines); hardcoded season year and bracket size (`Season==2024`, `Year==2026`, `index<64`) scattered across files instead of centralized in config; `.py`/`.ipynb` twins that drifted out of sync because notebook changes were manually "ported" to scripts; import-time side effects (training models / plotting on `import`).

## Rules & Coding Style

- No import-time side effects. Modules define functions/classes; execution happens via `scripts/` entry points or `if __name__ == "__main__"`.
- Notebooks (`notebooks/`) are exploration-only. Nothing in `src/` imports from a notebook, and notebook logic is never hand-copied into `src/` without being rewritten as tested functions.
- Season year, bracket size, round count, and play-in count come from `config/season.yaml` — never hardcode a year or team count in `src/`.
- One canonical implementation per model — no duplicate `.py`/`.ipynb` versions of the same logic.
- Comment aggressively per global standards: docstrings state Inputs, Outputs, Purpose, and any non-obvious logic (e.g., KenPom pagination quirks).

## Verification & Test Commands

Not yet established — no test suite or run commands exist. Update this section the moment `tests/` or `scripts/` are created.

## Fragile Areas

- **KenPom ingest**: raw export is manually copy/pasted (KenPom is subscription-gated and blocks scraping — do not attempt to automate the fetch itself). The paginated source table repeats its header row every ~40 teams and prints a rank subscript next to every stat column. `ingest/kenpom.py` must strip both before merging into history. Get this wrong and every downstream model silently trains on garbage rows.
- **Bracket structure at format-change boundaries**: the whole point of `bracket/structure.py` is to not hardcode round names or team counts. Any change that reintroduces a literal `R1`..`R6` or `64`/`68` constant outside `config/season.yaml` is a regression.
- **Women's tournament**: KenPom has no women's coverage. Do not assume the men's ingest pipeline generalizes — a different ratings source (candidate: Massey Ordinals, already in the Kaggle bundle) will be needed when this is tackled.

## Generated Artifacts

None yet. Once the pipeline exists: `data/processed/`, `data/outputs/`, and `reports/` will hold pipeline-generated files — gitignored, never hand-edited, always safe to delete and regenerate.
