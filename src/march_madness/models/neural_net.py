"""Small MLP win-probability classifier."""

from __future__ import annotations

from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_model(random_state: int = 42) -> Pipeline:
    """Scaled MLP -- gradient-based training is sensitive to feature scale."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=300, random_state=random_state),
            ),
        ]
    )
