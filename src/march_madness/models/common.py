"""
Shared data prep and evaluation for the four win-probability classifiers
(logistic_regression, random_forest, xgboost_model, neural_net). Every
legacy model script duplicated this same split/evaluate boilerplate with
small, inconsistent variations (different test_size per model, two
different ECE formulas); this is the one canonical version. Plotting code
from the legacy scripts (ROC curves, calibration plots, confusion matrices)
is deliberately not ported here -- that's a presentation concern for
Milestone 2, not a modeling one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from march_madness.features.build_features import conference_tier

STAT_COLUMNS = [
    "NetRtg", "ORtg", "DRtg", "AdjT", "Luck",
    "SOS_NetRtg", "SOS_ORtg", "SOS_DRtg", "NCSOS_NetRtg", "W", "L",
]


def prepare_model_matrix(games: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Inputs: matchup history from build_matchup_history() + randomize_matchup_sides()
            (one row per game, *_A/*_B suffixed KenPom stats, a Winner column).
    Outputs: (X, y) ready for a classifier -- KenPom stat columns for both
             sides plus a conference-tier feature, y = Winner.
    Purpose: excludes identifiers (GameID, TeamID_A/B, Team_A/B, Season) and
             leaky/mostly-missing columns from what the model sees:
             Score_A/B is the game's actual final score (unknown before the
             game happens); Seed_A/B is null for ~80% of rows since only
             tournament teams ever have a seed.
    """
    features = pd.DataFrame(index=games.index)
    for suffix in ("_A", "_B"):
        for col in STAT_COLUMNS:
            features[col + suffix] = games[col + suffix]
        features["ConfTier" + suffix] = games["Conf" + suffix].map(conference_tier)

    return features, games["Winner"]


def split_features(
    X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """One standard train/test split for every model -- the legacy scripts each used a different ratio."""
    return train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)


def _expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lower, upper in zip(bin_boundaries[:-1], bin_boundaries[1:]):
        in_bin = (y_prob > lower) & (y_prob <= upper)
        if in_bin.sum() == 0:
            continue
        bin_accuracy = y_true[in_bin].mean()
        bin_confidence = y_prob[in_bin].mean()
        ece += (in_bin.sum() / len(y_prob)) * abs(bin_confidence - bin_accuracy)
    return ece


def evaluate_classifier(model: ClassifierMixin, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    """
    Inputs: a fitted binary classifier and a held-out test set.
    Outputs: the core metrics every legacy model script computed by hand,
             as data rather than printed strings and plots.
    Purpose: one evaluation function instead of five near-identical copies.
    """
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "log_loss": log_loss(y_test, y_prob),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "brier_score": brier_score_loss(y_test, y_prob),
        "expected_calibration_error": _expected_calibration_error(y_test.to_numpy(), y_prob),
    }


def train_and_evaluate(
    model: ClassifierMixin, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42
) -> tuple[ClassifierMixin, dict[str, float]]:
    """Splits, fits, and evaluates in one call. Returns the fitted model and its metrics."""
    X_train, X_test, y_train, y_test = split_features(X, y, test_size, random_state)
    model.fit(X_train, y_train)
    return model, evaluate_classifier(model, X_test, y_test)
