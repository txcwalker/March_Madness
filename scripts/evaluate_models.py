"""
Trains all four win-probability models on the identical train/test split and
compares them: a metrics table (including expected calibration error, which
models/common.py already computes but run_pipeline.py never prints) plus a
real reliability diagram (predicted probability vs. actual observed win
rate), so "is this model actually calibrated" has a real answer instead of
just a backtest accuracy number.

Deliberately a script, not something added to src/march_madness/models/ --
plotting/comparison across models is a presentation/evaluation concern (see
models/common.py's module docstring), same reasoning as why run_pipeline.py
itself has no plotting.

Usage:
    python scripts/evaluate_models.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve

from march_madness.config import DEFAULT_CONFIG_PATH, load_season_config
from march_madness.features.build_features import build_matchup_history, randomize_matchup_sides
from march_madness.ingest.kaggle import load_kaggle_data
from march_madness.ingest.kenpom import build_kenpom_history
from march_madness.models import logistic_regression, neural_net, random_forest, xgboost_model
from march_madness.models.common import evaluate_classifier, prepare_model_matrix, split_features

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"

MODEL_MODULES = {
    "logistic_regression": logistic_regression,
    "random_forest": random_forest,
    "xgboost_model": xgboost_model,
    "neural_net": neural_net,
}


def main() -> None:
    config = load_season_config(DEFAULT_CONFIG_PATH)

    print("Loading data (same pipeline as run_pipeline.py)...")
    kaggle = load_kaggle_data(config.raw_dir / "kaggle")
    kenpom_history = build_kenpom_history(config.raw_dir.parent)
    history = build_matchup_history(kaggle, kenpom_history)
    games = randomize_matchup_sides(history, random_state=42)
    X, y = prepare_model_matrix(games)

    # Same split for every model so the comparison is apples-to-apples --
    # not each model picking its own best-case test set.
    X_train, X_test, y_train, y_test = split_features(X, y)
    print(f"{len(X_train)} training games, {len(X_test)} held-out test games\n")

    results = {}
    for name, module in MODEL_MODULES.items():
        print(f"Training {name}...")
        model = module.build_model()
        model.fit(X_train, y_train)
        metrics = evaluate_classifier(model, X_test, y_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        results[name] = {"metrics": metrics, "y_prob": y_prob}

    header = f"{'Model':22}{'Accuracy':>10}{'ROC AUC':>10}{'Log Loss':>10}{'Brier':>10}{'ECE':>10}"
    print("\n" + header)
    print("-" * len(header))
    for name, result in results.items():
        m = result["metrics"]
        print(
            f"{name:22}{m['accuracy']:>10.3f}{m['roc_auc']:>10.3f}{m['log_loss']:>10.3f}"
            f"{m['brier_score']:>10.3f}{m['expected_calibration_error']:>10.3f}"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot([0, 1], [0, 1], linestyle="--", color="#999999", label="Perfectly calibrated")
    for name, result in results.items():
        fraction_positive, mean_predicted = calibration_curve(y_test, result["y_prob"], n_bins=10, strategy="quantile")
        ax.plot(mean_predicted, fraction_positive, marker="o", label=name)
    ax.set_xlabel("Mean predicted win probability (per bin)")
    ax.set_ylabel("Actual observed win rate (per bin)")
    ax.set_title(f"Calibration -- held-out test set ({len(X_test)} games)")
    ax.legend()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    out_path = REPORTS_DIR / "model_calibration.png"
    fig.savefig(out_path, dpi=150)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
