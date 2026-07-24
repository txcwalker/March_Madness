"""XGBoost win-probability classifier."""

from __future__ import annotations

from xgboost import XGBClassifier


def build_model(random_state: int = 42) -> XGBClassifier:
    """
    No scaling -- tree splits are invariant to per-feature scaling, so it
    would be a no-op. Drops the legacy use_label_encoder=False param: that
    argument was removed from modern xgboost and raises a TypeError if passed.
    """
    return XGBClassifier(eval_metric="logloss", random_state=random_state)
