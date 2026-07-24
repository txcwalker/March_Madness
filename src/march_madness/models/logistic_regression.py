"""Logistic regression win-probability classifier."""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_model(random_state: int = 42) -> Pipeline:
    """Scaled logistic regression -- scaling matters for a linear model's coefficients and regularization."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1_000_000, random_state=random_state)),
        ]
    )
