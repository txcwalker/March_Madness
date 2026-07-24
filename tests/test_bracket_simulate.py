import numpy as np
import pandas as pd
import pytest

from march_madness.bracket.simulate import (
    build_seed_to_team,
    compute_win_probabilities,
    run_monte_carlo,
    simulate_bracket,
)
from march_madness.models.common import STAT_COLUMNS, build_prediction_matrix


def make_team_stats(team_ids: list[int]) -> pd.DataFrame:
    """One row per team, indexed by TeamID -- NetRtg equals the TeamID's last digit for an easy, legible signal."""
    rows = {tid: {"Conf": "sec", **{col: 100.0 for col in STAT_COLUMNS}} for tid in team_ids}
    for tid in team_ids:
        rows[tid]["NetRtg"] = float(tid % 100)
    return pd.DataFrame.from_dict(rows, orient="index")


class AlwaysHigherNetRtgWinsModel:
    """Fake classifier: team "_A" wins with certainty whenever its NetRtg_A > NetRtg_B."""

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        team_a_wins = (X["NetRtg_A"] > X["NetRtg_B"]).astype(float)
        return np.column_stack([1 - team_a_wins, team_a_wins])


def make_small_bracket() -> pd.DataFrame:
    """4-team bracket: S1 (seed1 vs seed2), S2 (seed3 vs seed4), FINAL (S1 winner vs S2 winner)."""
    return pd.DataFrame(
        {
            "Slot": ["S1", "S2", "FINAL"],
            "StrongSeed": ["seed1", "seed3", "S1"],
            "WeakSeed": ["seed2", "seed4", "S2"],
        }
    )


def test_build_seed_to_team_filters_by_season():
    seeds = pd.DataFrame(
        {"Season": [2025, 2025, 2026], "Seed": ["W01", "W02", "W01"], "TeamID": [1, 2, 3]}
    )

    result = build_seed_to_team(seeds, season=2026)

    assert result == {"W01": 3}


def test_build_prediction_matrix_shapes_pairs_correctly():
    team_stats = make_team_stats([101, 102])

    X = build_prediction_matrix(team_stats, [(101, 102)])

    assert X.loc[(101, 102), "NetRtg_A"] == 1.0
    assert X.loc[(101, 102), "NetRtg_B"] == 2.0
    assert "ConfTier_A" in X.columns


def test_compute_win_probabilities_favors_higher_net_rtg():
    team_stats = make_team_stats([101, 102, 103])
    model = AlwaysHigherNetRtgWinsModel()

    probs = compute_win_probabilities(model, team_stats, [101, 102, 103])

    assert probs[102][101] == 1.0  # 102 (NetRtg=2) beats 101 (NetRtg=1)
    assert probs[101][102] == 0.0
    assert probs[103][101] == 1.0  # 103 (NetRtg=3) beats 101


def test_simulate_bracket_deterministic_always_picks_the_favorite():
    slots = make_small_bracket()
    seed_to_team = {"seed1": 101, "seed2": 102, "seed3": 103, "seed4": 104}
    # 102 beats 101, 104 beats 103, 104 beats 102 -- so 104 wins it all
    probs = {
        101: {102: 0.0}, 102: {101: 1.0, 104: 0.0},
        103: {104: 0.0}, 104: {103: 1.0, 102: 1.0},
    }
    rng = np.random.default_rng(0)

    winners = simulate_bracket(slots, seed_to_team, probs, rng, deterministic=True)

    assert winners["S1"] == 102
    assert winners["S2"] == 104
    assert winners["FINAL"] == 104


def test_simulate_bracket_extreme_probabilities_are_deterministic_even_when_sampling():
    # p=1.0/0.0 leaves no room for randomness: rng.random() is always in [0, 1),
    # so "rng.random() < 1.0" is always true regardless of the draw.
    # 101 beats 102, 103 beats 104, 101 beats 103 in the final -- 101 wins it all.
    slots = make_small_bracket()
    seed_to_team = {"seed1": 101, "seed2": 102, "seed3": 103, "seed4": 104}
    probs = {
        101: {102: 1.0, 103: 1.0}, 102: {101: 0.0},
        103: {104: 1.0, 101: 0.0}, 104: {103: 0.0},
    }
    rng = np.random.default_rng(123)

    for _ in range(20):
        winners = simulate_bracket(slots, seed_to_team, probs, rng, deterministic=False)
        assert winners["S1"] == 101
        assert winners["S2"] == 103
        assert winners["FINAL"] == 101


def test_run_monte_carlo_shape_and_consistency_with_extreme_probabilities():
    slots = make_small_bracket()
    seed_to_team = {"seed1": 101, "seed2": 102, "seed3": 103, "seed4": 104}
    probs = {
        101: {102: 1.0, 103: 1.0}, 102: {101: 0.0},
        103: {104: 1.0, 101: 0.0}, 104: {103: 0.0},
    }

    results = run_monte_carlo(slots, seed_to_team, probs, n_brackets=50, random_state=42)

    assert len(results) == 50 * len(slots)
    final_winners = results[results["Slot"] == "FINAL"]["TeamID"]
    assert (final_winners == 101).all()


def test_run_monte_carlo_produces_variety_with_fair_coin_probabilities():
    slots = make_small_bracket()
    seed_to_team = {"seed1": 101, "seed2": 102, "seed3": 103, "seed4": 104}
    team_ids = [101, 102, 103, 104]
    probs = {t1: {t2: 0.5 for t2 in team_ids if t2 != t1} for t1 in team_ids}

    results = run_monte_carlo(slots, seed_to_team, probs, n_brackets=500, random_state=42)

    final_winners = results[results["Slot"] == "FINAL"]["TeamID"]
    # with a fair coin at every round, all 4 teams should show up as champion at least once in 500 tries
    assert final_winners.nunique() == 4
