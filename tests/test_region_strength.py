import pandas as pd
import pytest

from march_madness.analysis.region_strength import (
    region_competitiveness,
    region_effective_contenders,
    region_of_main_bracket_slot,
    strongest_team_by_region,
)

# A tiny two-region, four-team-per-region bracket (real games only need
# R1-R4 slot codes to be exercised -- this uses R1 and R2, which is enough
# to test both "fixed every bracket" and "depends on who actually won"
# games without needing a full 16-team/4-round region).
SLOTS = pd.DataFrame(
    {
        "Slot": ["R1W1", "R1W2", "R2W1", "R1X1", "R1X2", "R2X1"],
        "StrongSeed": ["W01", "W03", "R1W1", "X01", "X03", "R1X1"],
        "WeakSeed": ["W02", "W04", "R1W2", "X02", "X04", "R1X2"],
    }
)
SEED_TO_TEAM = {"W01": 11, "W02": 12, "W03": 13, "W04": 14, "X01": 21, "X02": 22, "X03": 23, "X04": 24}

# Symmetric win probabilities across all 8 teams, strongest (11) to weakest
# (24): P(a beats b) + P(b beats a) == 1 always, matching what
# bracket.simulate.compute_win_probabilities() guarantees post-symmetrization.
_STRENGTH_ORDER = [11, 12, 13, 14, 21, 22, 23, 24]
WIN_PROBABILITIES = {
    a: {b: 0.5 + 0.05 * (_STRENGTH_ORDER.index(b) - _STRENGTH_ORDER.index(a)) for b in _STRENGTH_ORDER if b != a}
    for a in _STRENGTH_ORDER
}

# Two simulated brackets. Region W has a real upset in bracket 2 (12 beats
# 11 in R1W1), so its Elite-Eight-equivalent game (R2W1) is a different
# matchup -- and a different Closeness value -- in each bracket. Region X
# is chalk in both brackets, so all three of its games are identical
# bracket to bracket -- the contrast this fixture is built to exercise.
RESULTS = pd.DataFrame(
    [
        {"Bracket": 1, "Slot": "R1W1", "TeamID": 11},
        {"Bracket": 1, "Slot": "R1W2", "TeamID": 13},
        {"Bracket": 1, "Slot": "R2W1", "TeamID": 11},
        {"Bracket": 1, "Slot": "R1X1", "TeamID": 21},
        {"Bracket": 1, "Slot": "R1X2", "TeamID": 23},
        {"Bracket": 1, "Slot": "R2X1", "TeamID": 21},
        {"Bracket": 2, "Slot": "R1W1", "TeamID": 12},
        {"Bracket": 2, "Slot": "R1W2", "TeamID": 13},
        {"Bracket": 2, "Slot": "R2W1", "TeamID": 13},
        {"Bracket": 2, "Slot": "R1X1", "TeamID": 21},
        {"Bracket": 2, "Slot": "R1X2", "TeamID": 23},
        {"Bracket": 2, "Slot": "R2X1", "TeamID": 21},
    ]
)


def _closeness(team1: int, team2: int) -> float:
    p_favorite = max(WIN_PROBABILITIES[team1][team2], WIN_PROBABILITIES[team2][team1])
    return 2 * (1 - p_favorite)


def test_region_of_main_bracket_slot_extracts_the_region_letter():
    assert region_of_main_bracket_slot("R1W1") == "W"
    assert region_of_main_bracket_slot("R4Z1") == "Z"
    # R5/R6 pair two different regions together -- not "one region's" game.
    assert region_of_main_bracket_slot("R5WX") is None
    assert region_of_main_bracket_slot("R6CH") is None
    # A play-in slot (bare region letter + seed number, no round digit).
    assert region_of_main_bracket_slot("X16") is None


def test_region_competitiveness_averages_outcome_uncertainty_across_all_region_games():
    result = region_competitiveness(SLOTS, SEED_TO_TEAM, WIN_PROBABILITIES, RESULTS)

    # Region W: R1W1 and R1W2 are fixed (same two teams every bracket), but
    # R2W1 depends on who actually won R1W1 -- team 11 in bracket 1 (chalk),
    # team 12 in bracket 2 (the upset) -- so its opponent, and its
    # Closeness, differs by bracket.
    expected_w = sum(
        [
            _closeness(11, 12),
            _closeness(13, 14),
            _closeness(11, 13),  # bracket 1's R2W1: 11 vs 13
            _closeness(11, 12),
            _closeness(13, 14),
            _closeness(12, 13),  # bracket 2's R2W1: 12 vs 13
        ]
    ) / 6
    assert result["W"] == pytest.approx(expected_w)

    # Region X never has an upset in either bracket -- all three of its
    # games are identical across both brackets.
    expected_x = sum([_closeness(21, 22), _closeness(23, 24), _closeness(21, 23)] * 2) / 6
    assert result["X"] == pytest.approx(expected_x)


def test_strongest_team_by_region_picks_by_win_probability_not_seed():
    team_to_region = {11: "W", 12: "W", 13: "W", 14: "W", 21: "X", 22: "X", 23: "X", 24: "X"}

    favorites = strongest_team_by_region(team_to_region, WIN_PROBABILITIES)

    assert favorites["W"] == 11
    assert favorites["X"] == 21


def test_region_effective_contenders_is_the_reciprocal_of_hhi():
    benefit = pd.DataFrame(
        [
            {"TeamX": 11, "TeamY": 12, "FinalFourShareIfXEliminated": 0.5},
            {"TeamX": 11, "TeamY": 13, "FinalFourShareIfXEliminated": 0.3},
            {"TeamX": 11, "TeamY": 14, "FinalFourShareIfXEliminated": 0.2},
            # Different region -- must be excluded from region "W"'s HHI.
            {"TeamX": 11, "TeamY": 21, "FinalFourShareIfXEliminated": 0.0},
        ]
    )
    team_to_region = {11: "W", 12: "W", 13: "W", 14: "W", 21: "X"}
    favorite_by_region = {"W": 11}

    result = region_effective_contenders(benefit, team_to_region, favorite_by_region)

    expected_hhi = 0.5**2 + 0.3**2 + 0.2**2
    assert result["W"] == pytest.approx(1 / expected_hhi)


def test_region_effective_contenders_matches_the_textbook_case():
    # A clean 50% favorite plus three genuinely equal backups should score
    # almost exactly 3 effective contenders -- the worked check from the
    # region-strength design conversation (WORKLOG 2026-08-03).
    benefit = pd.DataFrame(
        [
            {"TeamX": 11, "TeamY": 12, "FinalFourShareIfXEliminated": 1 / 6},
            {"TeamX": 11, "TeamY": 13, "FinalFourShareIfXEliminated": 1 / 6},
            {"TeamX": 11, "TeamY": 14, "FinalFourShareIfXEliminated": 1 / 6},
            {"TeamX": 11, "TeamY": 15, "FinalFourShareIfXEliminated": 0.5},
        ]
    )
    team_to_region = {11: "W", 12: "W", 13: "W", 14: "W", 15: "W"}
    favorite_by_region = {"W": 11}

    result = region_effective_contenders(benefit, team_to_region, favorite_by_region)

    assert result["W"] == pytest.approx(3.0)
