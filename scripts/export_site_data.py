"""
Exports data/outputs/<year>/*.csv into frontend-consumable JSON.

Reads the cached simulation_results.csv and reruns it through
march_madness.analysis, the same "stays fast, decoupled from
run_pipeline.py's runtime" role the superseded scripts/build_site.py played
for the Jinja2 site (see legacy/jinja_site/) -- just producing JSON for the
React frontend instead of rendering HTML.

Writes two files to the same directory: `<year>.json` (an immutable
per-season snapshot, for the future previous-years history view) and
`current.json` (always the most recently exported season -- what the
frontend actually fetches, so it never has to know the year ahead of time).

Usage:
    python scripts/export_site_data.py
    python scripts/export_site_data.py --config config/season.yaml --out frontend/public/data
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from march_madness.analysis import region_strength, round_advancement
from march_madness.config import DEFAULT_CONFIG_PATH, load_season_config

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "frontend" / "public" / "data"

# 8 seed thresholds x 5 rounds, matching the sweep the superseded Jinja2
# build used for its Cinderella heatmap (see legacy/jinja_site/).
CINDERELLA_SEED_THRESHOLDS = [9, 10, 11, 12, 13, 14, 15, 16]
CINDERELLA_ROUNDS = ["R2", "R3", "R4", "R5", "R6"]


def american_odds(probability: float) -> int:
    """
    Inputs: a win probability in [0, 1].
    Outputs: the equivalent American odds as a signed int (negative = favorite).
    Purpose: presentation only -- the model reasons in probabilities, but
             American odds are the familiar unit for this audience. 0% and
             100% aren't representable as finite odds, so they're capped at
             a clearly-a-longshot/lock sentinel instead of dividing by zero.
    """
    if probability <= 0:
        return 1_000_000
    if probability >= 1:
        return -1_000_000
    if probability >= 0.5:
        return round(-100 * probability / (1 - probability))
    return round(100 * (1 - probability) / probability)


def build_teams_payload(
    teams: pd.DataFrame,
    advancement: pd.DataFrame,
    wins_over_seed: pd.DataFrame,
    seed_by_team: dict[int, int],
    team_to_region: dict[int, str],
    n_brackets: int,
) -> list[dict]:
    """
    Inputs: the full teams.csv (every team actually in the field --
            TeamID/Seed/TeamName), round_advancement_counts() output,
            wins_over_seed_expectation() output, TeamID -> seed number, and
            the bracket count used to turn raw counts into probabilities.
    Outputs: one dict per team merging both analyses, with round-reach both
             as a percentage and as American odds.
    Purpose: single per-team record the frontend can render Round Odds,
             Home's stat strip, and Over/Underperformers from without doing
             its own pandas-style joins in JS.

             Anchoring on `teams` (not `advancement`) matters: with a
             sufficiently confident model (a real issue found switching to
             xgboost_model), a big enough underdog can lose every single
             game across all 10,000 simulated brackets and never appear as
             a winner in `results` at all -- round_advancement_counts()
             then silently drops that team from its output entirely,
             the exact same class of bug average_wins_by_team() already
             guards against elsewhere (see its docstring). Left-joining
             onto the full team list and filling missing rounds with 0
             keeps every real tournament team in the export, correctly
             showing them at effectively 0% instead of vanishing.
    """
    round_columns = {
        "Round of 32": "roundOf32",
        "Sweet Sixteen": "sweetSixteen",
        "Elite Eight": "eliteEight",
        "Final Four": "finalFour",
        "Championship Game": "championshipGame",
        "Champion": "champion",
    }

    merged = teams.merge(advancement.drop(columns=["Team"]), on="TeamID", how="left")
    for csv_col in round_columns:
        merged[csv_col] = merged[csv_col].fillna(0)
    merged = merged.merge(
        wins_over_seed[["TeamID", "SimulatedAverageWins", "HistoricalAverageWins", "WinsOverSeedExpectation"]],
        on="TeamID",
        how="left",
    )

    payload = []
    for row in merged.to_dict("records"):
        record = {
            "teamId": int(row["TeamID"]),
            "team": row["TeamName"],
            "seed": seed_by_team.get(row["TeamID"]),
            "region": team_to_region.get(row["TeamID"]),
            "simulatedAverageWins": round(float(row["SimulatedAverageWins"]), 3),
            "historicalAverageWins": row["HistoricalAverageWins"],
            "winsOverSeedExpectation": round(float(row["WinsOverSeedExpectation"]), 3),
        }
        for csv_col, json_key in round_columns.items():
            count = int(row[csv_col])
            probability = count / n_brackets
            record[json_key] = {
                "probability": round(probability, 4),
                "odds": american_odds(probability),
            }
        payload.append(record)

    payload.sort(key=lambda t: t["champion"]["probability"], reverse=True)
    return payload


def build_region_payload(
    results: pd.DataFrame,
    seed_to_team: dict[str, int],
    id_to_team: pd.Series,
    team_to_region: dict[int, str],
    benefit: pd.DataFrame,
    region_competitiveness_df: pd.DataFrame | None,
) -> list[dict]:
    """
    Region-level championship share plus two complementary families of
    "how strong/fragile is this region" stats. `topSeedFinalFourShare`
    (not `topSeedChampionshipShare`) is the headline top-seed-dominance
    figure as of 2026-07-30 -- a real audit found the championship-
    conditioned version both conflates a region's own competitiveness with
    cross-region championship-game strength, and is statistically unstable
    for any region that rarely wins it all (see analysis/region_strength.py
    docstrings for the full reasoning and real numbers). The championship-
    conditioned share is still exported as a secondary figure, not dropped.

    `competitiveness` and `effectiveContenders` (2026-08-03) answer a
    different question those top-seed-dominance stats can't: whether the
    region's own games are actually close, and how open the region is if
    its favorite doesn't come through -- see analysis/region_strength.py's
    region_competitiveness()/region_effective_contenders() docstrings and
    WORKLOG for why a region can score as "dominant" by the top-seed stats
    while still being genuinely competitive by these, or vice versa.
    `competitiveness`/`favoriteTeamId` come from region_competitiveness.csv
    (written by run_pipeline.py, since they need the win-probability
    matrix -- absent if that file hasn't been generated yet, e.g. an older
    run_pipeline.py output directory). `effectiveContenders` is computed
    here from `benefit` (already built from simulation_results.csv for the
    Who Benefits payload, reused rather than recomputed) plus that CSV's
    favorite-team column.
    """
    champ_counts = region_strength.region_championship_counts(results, seed_to_team)
    final_four_share = region_strength.region_top_seed_final_four_share(results, seed_to_team)
    championship_share = region_strength.region_top_seed_championship_share(results, seed_to_team)
    total = int(champ_counts.sum())

    top_seed_by_region = {
        region_strength.region_of_seed(seed): team_id for seed, team_id in seed_to_team.items() if seed[1:3] == "01"
    }

    competitiveness_by_region: dict[str, float] = {}
    favorite_by_region: dict[str, int] = {}
    if region_competitiveness_df is not None:
        for row in region_competitiveness_df.itertuples():
            competitiveness_by_region[row.Region] = float(row.Competitiveness)
            favorite_by_region[row.Region] = int(row.FavoriteTeamID)
    effective_contenders = (
        region_strength.region_effective_contenders(benefit, team_to_region, favorite_by_region)
        if favorite_by_region
        else pd.Series(dtype=float)
    )

    regions = []
    for region in sorted(set(champ_counts.index) | set(final_four_share.index)):
        favorite_team_id = favorite_by_region.get(region)
        contenders = effective_contenders.get(region)
        regions.append(
            {
                "region": region,
                "championshipShare": round(champ_counts.get(region, 0) / total, 4) if total else 0.0,
                "topSeedFinalFourShare": round(float(final_four_share.get(region, 0.0)), 4),
                "topSeedChampionshipShare": round(float(championship_share.get(region, 0.0)), 4),
                "topSeedTeamId": top_seed_by_region.get(region),
                "topSeedTeam": id_to_team.get(top_seed_by_region.get(region)),
                "competitiveness": (
                    round(competitiveness_by_region[region], 4) if region in competitiveness_by_region else None
                ),
                "favoriteTeamId": favorite_team_id,
                "favoriteTeam": id_to_team.get(favorite_team_id) if favorite_team_id is not None else None,
                "effectiveContenders": round(float(contenders), 4) if pd.notna(contenders) else None,
            }
        )
    regions.sort(key=lambda r: r["championshipShare"], reverse=True)
    return regions


def build_final_four_payload(results: pd.DataFrame, id_to_team: pd.Series, n_brackets: int) -> list[dict]:
    """
    Every unique Final Four combination that occurred in any simulated
    bracket (see analysis/round_advancement.py), not just a top-N slice --
    the Final Four Finder page needs the full list so an arbitrary partial
    team selection can be looked up honestly, including truthfully
    returning zero for a combination that was never simulated. In practice
    this tops out in the low hundreds of unique combinations even across
    10,000 brackets, so exporting all of them is cheap.
    """
    combos = round_advancement.final_four_combination_counts(results)
    return [
        {
            "teamIds": list(team_ids),
            "teams": [id_to_team.get(team_id, str(team_id)) for team_id in team_ids],
            "count": int(count),
            "probability": round(count / n_brackets, 4),
        }
        for team_ids, count in combos.items()
    ]


def build_path_of_least_resistance_payload(path_ease: pd.DataFrame, id_to_team: pd.Series) -> list[dict]:
    """
    Inputs: path_of_least_resistance.csv (written by run_pipeline.py, since
            it needs the win-probability matrix and the raw per-bracket
            Monte Carlo results -- only available there, not from
            simulation_results.csv's on-disk aggregate form) and the
            TeamID -> name lookup.
    Outputs: one dict per team with its average opponent strength faced at
             each of the four rounds, PathStrengthFaced (the primary,
             seed-agnostic "how tough is the draw" number -- see
             analysis/bracket_path.py's module docstring), and PathEase
             (the secondary, team-relative "are you still favored" number).
             Sorted easiest-draw-first by PathStrengthFaced (already sorted
             this way in the CSV, re-sorted here defensively).
    """
    strength_columns = {
        "RoundOf32Strength": "roundOf32Strength",
        "SweetSixteenStrength": "sweetSixteenStrength",
        "EliteEightStrength": "eliteEightStrength",
        "FinalFourStrength": "finalFourStrength",
    }
    rows = []
    for row in path_ease.to_dict("records"):
        record = {
            "teamId": int(row["TeamID"]),
            "team": id_to_team.get(row["TeamID"], str(row["TeamID"])),
            "pathStrengthFaced": round(float(row["PathStrengthFaced"]), 4),
            "pathEase": round(float(row["PathEase"]), 4),
        }
        for csv_col, json_key in strength_columns.items():
            value = row[csv_col]
            record[json_key] = round(float(value), 4) if pd.notna(value) else None
        rows.append(record)
    rows.sort(key=lambda r: r["pathStrengthFaced"])
    return rows


def build_benefit_if_loses_payload(benefit: pd.DataFrame, id_to_team: pd.Series) -> dict[str, list[dict]]:
    """
    Inputs: analysis.round_advancement.benefit_if_team_loses()'s output
            (computed once in main() -- also reused by build_region_payload
            for region_effective_contenders(), so it isn't recomputed here)
            and the TeamID -> name lookup.
    Outputs: {TeamX's TeamID (as a string, since JSON object keys are always
             strings) -> the FULL list of every other team's benefit if
             TeamX doesn't reach the Final Four (not capped -- the frontend
             independently ranks and slices Final Four odds by
             finalFourBenefit and championship odds by championBenefit,
             since those two rankings surface different teams; a single
             server-side sort/cap would throw away one of them). Default
             order here is by ChampionBenefit, but that's just a
             convenience default, not load-bearing.
    Purpose: the "Who Benefits if Team X Loses" page picks a team from a
             dropdown and shows this list directly -- see
             analysis/round_advancement.py's benefit_if_team_loses() for
             what "loses" means here (doesn't reach the Final Four), and
             why Final Four odds are region-scoped but championship odds
             are not (a different-region team's Final Four odds can't
             actually be affected by TeamX at all -- any nonzero number
             there would be Monte Carlo noise, not a real effect -- but
             their championship odds have a real cross-region dependency).
    """
    payload: dict[str, list[dict]] = {}
    for team_x, group in benefit.groupby("TeamX"):
        ranked = group.sort_values("ChampionBenefit", ascending=False)
        payload[str(int(team_x))] = [
            {
                "teamId": int(row.TeamY),
                "team": id_to_team.get(row.TeamY, str(row.TeamY)),
                "championBenefit": round(float(row.ChampionBenefit), 4),
                "championShareBaseline": round(float(row.ChampionShareBaseline), 4),
                "championShareIfXEliminated": round(float(row.ChampionShareIfXEliminated), 4),
                "finalFourBenefit": round(float(row.FinalFourBenefit), 4),
                "finalFourShareBaseline": round(float(row.FinalFourShareBaseline), 4),
                "finalFourShareIfXEliminated": round(float(row.FinalFourShareIfXEliminated), 4),
            }
            for row in ranked.itertuples()
        ]
    return payload


def build_cinderella_payload(results: pd.DataFrame, seed_by_team: dict[int, int]) -> list[dict]:
    """8 seed thresholds x 5 rounds -> probability at least one that-seed-or-worse team reached that round."""
    return [
        {
            "minSeed": min_seed,
            "round": round_code,
            "probability": round(
                round_advancement.cinderella_probability(results, seed_by_team, min_seed, round_code), 4
            ),
        }
        for min_seed in CINDERELLA_SEED_THRESHOLDS
        for round_code in CINDERELLA_ROUNDS
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    config = load_season_config(args.config)
    outputs = config.outputs_dir

    results_path = outputs / "simulation_results.csv"
    teams_path = outputs / "teams.csv"
    if not results_path.exists() or not teams_path.exists():
        raise SystemExit(
            f"Missing {results_path} or {teams_path} -- run `python scripts/run_pipeline.py` first."
        )

    results = pd.read_csv(results_path)
    teams = pd.read_csv(teams_path)

    path_ease_path = outputs / "path_of_least_resistance.csv"
    path_ease = pd.read_csv(path_ease_path) if path_ease_path.exists() else None

    region_competitiveness_path = outputs / "region_competitiveness.csv"
    region_competitiveness_df = pd.read_csv(region_competitiveness_path) if region_competitiveness_path.exists() else None

    # seed_predictions.csv / team_tiers.csv are deliberately NOT included yet:
    # both are keyed by KenPom's raw team-name string, not Kaggle's TeamID
    # (seed_knn/seed_clustering operate on KenPom data directly and never see
    # a TeamID). Joining them here by exact name string would reintroduce
    # the same silent-mismatch risk `match_kenpom_teams()` exists to fix
    # elsewhere (see AGENTS.md Fragile Areas: exact-name matching drops
    # ~38% of teams on real data). Fold them in properly when building the
    # Seed Prediction page, not with a naive merge here.

    n_brackets = int(results["Bracket"].nunique())
    id_to_team = teams.set_index("TeamID")["TeamName"]
    seed_to_team = dict(zip(teams["Seed"], teams["TeamID"]))
    seed_by_team = {int(row.TeamID): int(row.Seed[1:3]) for row in teams.itertuples()}
    team_to_region = {int(row.TeamID): region_strength.region_of_seed(row.Seed) for row in teams.itertuples()}

    advancement = round_advancement.round_advancement_counts(results)
    advancement["Team"] = advancement["TeamID"].map(id_to_team)
    wins_over_seed = round_advancement.wins_over_seed_expectation(results, seed_by_team)

    # Computed once, shared by both the Who Benefits payload and
    # region_effective_contenders() (see build_region_payload's docstring)
    # rather than built twice.
    benefit = round_advancement.benefit_if_team_loses(results, list(seed_to_team.values()), team_to_region)

    payload = {
        "season": config.year,
        "nBrackets": n_brackets,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "teams": build_teams_payload(teams, advancement, wins_over_seed, seed_by_team, team_to_region, n_brackets),
        "regions": build_region_payload(
            results, seed_to_team, id_to_team, team_to_region, benefit, region_competitiveness_df
        ),
        "finalFourCombos": build_final_four_payload(results, id_to_team, n_brackets),
        "cinderella": build_cinderella_payload(results, seed_by_team),
        "pathOfLeastResistance": (
            build_path_of_least_resistance_payload(path_ease, id_to_team) if path_ease is not None else []
        ),
        "benefitIfLoses": build_benefit_if_loses_payload(benefit, id_to_team),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    season_path = args.out / f"{config.year}.json"
    current_path = args.out / "current.json"
    season_path.write_text(json.dumps(payload, indent=2))
    current_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {season_path}")
    print(f"Wrote {current_path}")


if __name__ == "__main__":
    main()
