"""
End-to-end pipeline: ingest -> features -> train a model -> simulate the
bracket -> analysis. Wires together every module built in Milestone 1 into
one runnable command, replacing the one-off scripts used to verify them
individually.

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --model random_forest --n-brackets 5000
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from march_madness.analysis import region_strength, round_advancement
from march_madness.bracket.simulate import build_seed_to_team, compute_win_probabilities, run_monte_carlo
from march_madness.bracket.structure import (
    MAIN_BRACKET_SIZE,
    is_play_in_slot,
    order_slots_for_simulation,
    validate_slots,
)
from march_madness.config import BracketConfig, DEFAULT_CONFIG_PATH, load_season_config
from march_madness.features.build_features import (
    build_matchup_history,
    match_kenpom_teams,
    randomize_matchup_sides,
)
from march_madness.ingest.kaggle import load_kaggle_data
from march_madness.ingest.kenpom import build_kenpom_history
from march_madness.models import logistic_regression, neural_net, random_forest, seed_clustering, seed_knn, xgboost_model
from march_madness.models.common import prepare_model_matrix, train_and_evaluate

MODEL_MODULES = {
    "logistic_regression": logistic_regression,
    "random_forest": random_forest,
    "xgboost_model": xgboost_model,
    "neural_net": neural_net,
}


def derive_bracket_config(season_slots) -> BracketConfig:
    """
    Inputs: one season's slots from Kaggle's raw data.
    Outputs: a BracketConfig matching what's actually in that data.
    Purpose: a given season's real slots file may not match
             config/season.yaml's declared bracket.num_play_in_games (e.g.
             the 2026 snapshot in this project has First Four already
             resolved into a clean 64-team field with zero play-in rows,
             unlike 2024's data -- see AGENTS.md Fragile Areas). Deriving
             the structure from the real data is more robust than trusting
             a static config value for the simulation step specifically.
    """
    num_play_in = int(season_slots["Slot"].map(is_play_in_slot).sum())
    return BracketConfig(size=MAIN_BRACKET_SIZE + num_play_in, num_rounds=6, num_play_in_games=num_play_in)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    # Default is xgboost_model as of 2026-07-30. History: briefly tried
    # xgboost_model on a single populated season (2026 only, 5,265 games),
    # found via scripts/evaluate_models.py that it was worse than
    # logistic_regression on every metric (accuracy 0.681 vs 0.745, ECE 0.145
    # vs 0.032) and reverted to logistic_regression. Traced the real cause to
    # training-data starvation, not model choice -- fixed with
    # scripts/backfill_historical_kenpom.py (2003-2025 imported from the
    # legacy project, 24 seasons / ~117K games total). Re-ran the comparison:
    # xgboost_model accuracy 0.744 vs logistic_regression's 0.755, ECE 0.024
    # vs 0.012 -- close enough, and judged to capture real nonlinear
    # structure the linear model can't, that the user chose it as the live
    # default. A real hyperparameter-tuned comparison is still open
    # Milestone 3 work; this is "best available today," not a final verdict.
    parser.add_argument("--model", choices=sorted(MODEL_MODULES), default="xgboost_model")
    parser.add_argument("--n-brackets", type=int, default=10_000)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    config = load_season_config(args.config)
    config.ensure_data_dirs()
    print(f"=== March Madness pipeline: {config.year} season ===")

    print("\n[1/6] Loading Kaggle data...")
    kaggle = load_kaggle_data(config.raw_dir / "kaggle")

    print("[1/6] Building KenPom history from every year found under data/raw/...")
    kenpom_history = build_kenpom_history(config.raw_dir.parent)

    print("\n[2/6] Matching KenPom teams to Kaggle TeamIDs...")
    matched_kenpom, unmatched = match_kenpom_teams(kenpom_history, kaggle.team_spellings)
    if len(unmatched):
        unmatched_teams = unmatched[["Team", "Season"]].drop_duplicates()
        print(f"  {len(unmatched_teams)} KenPom team-season(s) did not match MTeamSpellings.csv:")
        print(unmatched_teams.to_string(index=False))

    print("[2/6] Building matchup history and training features...")
    history = build_matchup_history(kaggle, kenpom_history)
    games = randomize_matchup_sides(history, random_state=42)
    X, y = prepare_model_matrix(games)
    print(f"  {len(X)} historical games, {X.shape[1]} features")

    print(f"\n[3/6] Training {args.model}...")
    model, metrics = train_and_evaluate(MODEL_MODULES[args.model].build_model(), X, y)
    print(
        f"  accuracy={metrics['accuracy']:.3f}  roc_auc={metrics['roc_auc']:.3f}  "
        f"log_loss={metrics['log_loss']:.3f}  brier={metrics['brier_score']:.3f}"
    )

    print(f"\n[4/6] Simulating {args.n_brackets} brackets for {config.year}...")
    season_slots = kaggle.slots[kaggle.slots["Season"] == config.year]
    if season_slots.empty:
        raise SystemExit(f"No bracket slots found for season {config.year} in the Kaggle data.")

    bracket_config = derive_bracket_config(season_slots)
    if bracket_config.num_play_in_games != config.bracket.num_play_in_games:
        print(
            f"  Note: config/season.yaml declares {config.bracket.num_play_in_games} play-in "
            f"game(s), but the real {config.year} data has {bracket_config.num_play_in_games}. "
            "Using what's actually in the data."
        )
    validate_slots(season_slots, bracket_config)
    ordered_slots = order_slots_for_simulation(season_slots)

    seed_to_team = build_seed_to_team(kaggle.seeds, season=config.year)
    if not seed_to_team:
        raise SystemExit(f"No seeds found for season {config.year} in the Kaggle data.")

    team_stats = matched_kenpom[matched_kenpom["Season"] == config.year].set_index("TeamID")
    missing_teams = [team_id for team_id in seed_to_team.values() if team_id not in team_stats.index]
    if missing_teams:
        print(f"  {len(missing_teams)} tournament team(s) missing KenPom stats -- substituting field-average stats")
        average_stats = team_stats.drop(columns=["Team", "Season", "Seed"]).mean(numeric_only=True)
        average_stats["Conf"] = team_stats["Conf"].mode().iloc[0]
        for team_id in missing_teams:
            team_stats.loc[team_id] = average_stats

    win_probs = compute_win_probabilities(model, team_stats, list(seed_to_team.values()))
    results = run_monte_carlo(ordered_slots, seed_to_team, win_probs, n_brackets=args.n_brackets, random_state=42)

    results_path = config.outputs_dir / "simulation_results.csv"
    results.to_csv(results_path, index=False)
    print(f"  wrote {results_path}")

    print("\n[5/6] Summarizing results...")
    id_to_team = kaggle.teams.set_index("TeamID")["TeamName"]
    seed_by_team = {team_id: int(seed[1:3]) for seed, team_id in seed_to_team.items()}

    advancement = round_advancement.round_advancement_counts(results)
    advancement["Team"] = advancement["TeamID"].map(id_to_team)
    advancement_path = config.outputs_dir / "round_advancement.csv"
    advancement.to_csv(advancement_path, index=False)
    print(f"  wrote {advancement_path}")

    if "Champion" in advancement.columns:
        top_champions = advancement.sort_values("Champion", ascending=False).head(10)
        print("\nTop simulated champions:")
        for _, row in top_champions.iterrows():
            print(f"  {row['Team']:25s} {row['Champion'] / args.n_brackets:.1%}")

    region_champs = region_strength.region_championship_counts(results, seed_to_team)
    region_shares = region_strength.region_top_seed_championship_share(results, seed_to_team)
    print("\nRegion championship share held by each region's #1 seed:")
    for region in sorted(region_shares.index):
        print(f"  {region}: {region_shares[region]:.1%}  ({region_champs.get(region, 0)} championships)")

    # Written so scripts/build_site.py can render pages purely from data/outputs/
    # (Seed, TeamName, etc.) without re-ingesting the raw Kaggle/KenPom data itself.
    teams_path = config.outputs_dir / "teams.csv"
    pd.DataFrame(
        [
            {"TeamID": team_id, "Seed": seed, "TeamName": id_to_team.get(team_id, str(team_id))}
            for seed, team_id in seed_to_team.items()
        ]
    ).to_csv(teams_path, index=False)
    print(f"  wrote {teams_path}")

    print(f"\n[6/6] Seed prediction and team tiering for {config.year}...")
    seed_model, seed_metrics, best_k = seed_knn.train_and_evaluate(kenpom_history)
    print(f"  seed_knn: best_k={best_k}  accuracy={seed_metrics['accuracy']:.3f}  mean_absolute_seed_error={seed_metrics['mean_absolute_seed_error']:.2f}")

    current_year_kenpom = kenpom_history[kenpom_history["Season"] == config.year]
    X_current, y_current = seed_knn.prepare_seed_matrix(current_year_kenpom)
    seed_predictions_path = config.outputs_dir / "seed_predictions.csv"
    current_year_kenpom[current_year_kenpom["Seed"].notna()][["Team", "Seed"]].assign(
        PredictedSeed=seed_model.predict(X_current)
    ).reset_index(drop=True).to_csv(seed_predictions_path, index=False)
    print(f"  wrote {seed_predictions_path}")

    clustered = seed_clustering.cluster_teams(current_year_kenpom, n_clusters=5)
    team_tiers_path = config.outputs_dir / "team_tiers.csv"
    clustered[["Team", "NetRtg", "Tier"]].sort_values("NetRtg", ascending=False).to_csv(
        team_tiers_path, index=False
    )
    print(f"  wrote {team_tiers_path}")

    print(f"\nDone. Outputs written to {config.outputs_dir}")


if __name__ == "__main__":
    main()
