"""
KNN seed-prediction model: given a tournament team's KenPom stats, predicts
its seed line (1-16). Distinct from the win-probability models above --
trains on one row per team-season, not per matchup, and only on the subset
of teams that actually made the tournament (i.e. have a known Seed).
"""

from __future__ import annotations

import pandas as pd
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from march_madness.features.build_features import conference_tier

STAT_COLUMNS = [
    "NetRtg", "ORtg", "DRtg", "AdjT", "Luck",
    "SOS_NetRtg", "SOS_ORtg", "SOS_DRtg", "NCSOS_NetRtg", "W", "L",
]


def prepare_seed_matrix(kenpom_history: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Inputs: cleaned, multi-year KenPom history (Team, Conf, stat columns, Seed, Season).
    Outputs: (X, y) for the seed-prediction model -- one row per team-season
             that has a known tournament seed. Regular-season-only teams
             have no Seed and are excluded here, not imputed.
    """
    tourney_teams = kenpom_history[kenpom_history["Seed"].notna()]

    features = tourney_teams[STAT_COLUMNS].copy()
    features["ConfTier"] = tourney_teams["Conf"].map(conference_tier)

    seeds = tourney_teams["Seed"].astype(int)
    return features.reset_index(drop=True), seeds.reset_index(drop=True)


def build_model(n_neighbors: int = 5) -> Pipeline:
    """Scaled KNN -- a distance-based model, so feature scale matters even more than for logistic regression."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", KNeighborsClassifier(n_neighbors=n_neighbors)),
        ]
    )


def tune_n_neighbors(X: pd.DataFrame, y: pd.Series, k_range: range = range(1, 31), cv: int = 5) -> int:
    """Grid search over n_neighbors, ported from the legacy seed_prediction.py's manual sweep."""
    param_grid = {"classifier__n_neighbors": list(k_range)}
    grid_search = GridSearchCV(build_model(), param_grid, cv=cv)
    grid_search.fit(X, y)
    return grid_search.best_params_["classifier__n_neighbors"]


def evaluate_seed_model(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    """
    Outputs: accuracy plus mean absolute seed error. Seed is an ordinal
             target -- predicting 2 instead of 1 and predicting 16 instead
             of 1 are very different misses that plain accuracy can't tell apart.
    """
    y_pred = model.predict(X_test)
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "mean_absolute_seed_error": mean_absolute_error(y_test, y_pred),
    }


def train_and_evaluate(
    kenpom_history: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
) -> tuple[Pipeline, dict[str, float], int]:
    """Prepares data, tunes n_neighbors, trains, and evaluates in one call."""
    X, y = prepare_seed_matrix(kenpom_history)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    best_k = tune_n_neighbors(X_train, y_train)
    model = build_model(n_neighbors=best_k)
    model.fit(X_train, y_train)

    return model, evaluate_seed_model(model, X_test, y_test), best_k
