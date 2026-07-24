"""Random forest win-probability classifier."""

from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier


def build_model(random_state: int = 42) -> RandomForestClassifier:
    """No scaling -- decision tree splits are invariant to per-feature scaling, so it would be a no-op."""
    return RandomForestClassifier(n_estimators=100, random_state=random_state)
