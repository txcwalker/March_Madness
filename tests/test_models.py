import numpy as np
import pandas as pd
import pytest

from march_madness.models import logistic_regression, neural_net, random_forest, seed_knn, xgboost_model
from march_madness.models.common import (
    evaluate_classifier,
    prepare_model_matrix,
    split_features,
    train_and_evaluate,
)

STAT_COLUMNS = [
    "NetRtg", "ORtg", "DRtg", "AdjT", "Luck",
    "SOS_NetRtg", "SOS_ORtg", "SOS_DRtg", "NCSOS_NetRtg", "W", "L",
]


def make_synthetic_games(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """
    Mimics build_matchup_history() + randomize_matchup_sides() output shape,
    with a real learnable signal (A wins more often when NetRtg_A > NetRtg_B)
    so the models being tested can do better than a coin flip.
    """
    rng = np.random.default_rng(seed)
    net_rtg_a = rng.normal(0, 15, n)
    net_rtg_b = rng.normal(0, 15, n)
    win_prob = 1 / (1 + np.exp(-(net_rtg_a - net_rtg_b) / 5))
    winner = rng.random(n) < win_prob

    df = pd.DataFrame(
        {
            "GameID": range(n),
            "Season": 2026,
            "TeamID_A": rng.integers(1100, 1500, n),
            "Score_A": rng.integers(50, 100, n),
            "Team_A": [f"TeamA{i}" for i in range(n)],
            "Conf_A": rng.choice(["sec", "big_twelve", "some_small_conf"], n),
            "TeamID_B": rng.integers(1100, 1500, n),
            "Score_B": rng.integers(50, 100, n),
            "Team_B": [f"TeamB{i}" for i in range(n)],
            "Conf_B": rng.choice(["sec", "big_twelve", "some_small_conf"], n),
            "Seed_A": np.where(rng.random(n) < 0.2, rng.integers(1, 17, n), np.nan),
            "Seed_B": np.nan,
            "Winner": winner.astype(int),
        }
    )
    df["NetRtg_A"] = net_rtg_a
    df["NetRtg_B"] = net_rtg_b
    for col in [c for c in STAT_COLUMNS if c != "NetRtg"]:
        df[col + "_A"] = rng.normal(100, 10, n)
        df[col + "_B"] = rng.normal(100, 10, n)
    return df


def make_synthetic_kenpom_history(n_teams_per_season: int = 40, seasons: tuple = (2024, 2025, 2026)) -> pd.DataFrame:
    """One row per team-season, with a real signal: higher NetRtg -> lower (better) seed."""
    rng = np.random.default_rng(1)
    rows = []
    for season in seasons:
        net_rtgs = rng.normal(10, 15, n_teams_per_season)
        order = np.argsort(-net_rtgs)  # best NetRtg first
        seeds = np.empty(n_teams_per_season)
        seeds[order] = np.repeat(np.arange(1, 17), np.ceil(n_teams_per_season / 16))[:n_teams_per_season]
        # only the top 68-ish teams (here: all of them, small synthetic pool) get a real seed
        for i in range(n_teams_per_season):
            row = {
                "Team": f"Team{season}_{i}",
                "Conf": rng.choice(["sec", "big_twelve", "some_small_conf"]),
                "Season": season,
                "Seed": seeds[i],
                "NetRtg": net_rtgs[i],
            }
            for col in [c for c in STAT_COLUMNS if c != "NetRtg"]:
                row[col] = rng.normal(100, 10)
            rows.append(row)
    return pd.DataFrame(rows)


def test_prepare_model_matrix_excludes_leaky_and_identifier_columns():
    games = make_synthetic_games(n=50)
    X, y = prepare_model_matrix(games)

    for leaky_col in ["GameID", "Season", "TeamID_A", "TeamID_B", "Team_A", "Team_B", "Score_A", "Score_B", "Seed_A", "Seed_B"]:
        assert leaky_col not in X.columns
    assert "NetRtg_A" in X.columns
    assert "ConfTier_A" in X.columns
    assert not X.isna().any().any()
    assert (y == games["Winner"]).all()


def test_split_features_respects_test_size():
    games = make_synthetic_games(n=200)
    X, y = prepare_model_matrix(games)

    X_train, X_test, y_train, y_test = split_features(X, y, test_size=0.25)

    assert len(X_test) == 50
    assert len(X_train) == 150


def test_evaluate_classifier_perfect_predictions_score_perfectly():
    class PerfectModel:
        def predict(self, X):
            return X["y_true"].to_numpy()

        def predict_proba(self, X):
            preds = X["y_true"].to_numpy()
            return np.column_stack([1 - preds, preds])

    y_test = pd.Series([0, 1, 1, 0, 1])
    X_test = pd.DataFrame({"y_true": y_test})

    metrics = evaluate_classifier(PerfectModel(), X_test, y_test)

    assert metrics["accuracy"] == 1.0
    assert metrics["log_loss"] < 1e-6
    assert metrics["expected_calibration_error"] < 1e-6


@pytest.mark.parametrize(
    "model_module",
    [logistic_regression, random_forest, xgboost_model, neural_net],
)
def test_each_classifier_builds_trains_and_beats_a_coin_flip(model_module):
    games = make_synthetic_games(n=300)
    X, y = prepare_model_matrix(games)

    model = model_module.build_model(random_state=42)
    fitted_model, metrics = train_and_evaluate(model, X, y)

    assert hasattr(fitted_model, "predict_proba")
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["accuracy"] > 0.6  # the synthetic signal is strong; a working model should clear this easily
    assert 0.0 <= metrics["roc_auc"] <= 1.0


def test_random_forest_and_xgboost_do_not_scale_features():
    # tree-based models should be bare estimators, not scaler pipelines
    assert not hasattr(random_forest.build_model(), "named_steps")
    assert not hasattr(xgboost_model.build_model(), "named_steps")


def test_logistic_regression_and_neural_net_scale_features():
    assert "scaler" in logistic_regression.build_model().named_steps
    assert "scaler" in neural_net.build_model().named_steps


def test_prepare_seed_matrix_excludes_teams_without_a_seed():
    history = make_synthetic_kenpom_history(n_teams_per_season=20, seasons=(2026,))
    history.loc[history.index[:5], "Seed"] = np.nan

    X, y = seed_knn.prepare_seed_matrix(history)

    assert len(X) == len(history) - 5
    assert y.notna().all()
    assert "ConfTier" in X.columns


def test_seed_knn_tune_and_train_beats_naive_baseline():
    history = make_synthetic_kenpom_history(n_teams_per_season=60, seasons=(2023, 2024, 2025, 2026))

    model, metrics, best_k = seed_knn.train_and_evaluate(history)

    assert best_k >= 1
    # naive baseline: always predict the mean seed (~8.5) -> MAE would be roughly 4-5
    assert metrics["mean_absolute_seed_error"] < 4.0
