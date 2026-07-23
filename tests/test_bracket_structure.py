import pandas as pd
import pytest

from march_madness.bracket.structure import (
    MAIN_BRACKET_SIZE,
    expected_slot_count,
    is_play_in_slot,
    order_slots_for_simulation,
    round_name,
    round_of,
    validate_bracket_config,
    validate_slots,
)
from march_madness.config import BracketConfig

REGIONS = ["W", "X", "Y", "Z"]


def build_main_bracket_rows(season: int) -> list[dict]:
    """The fixed 63-row, 64-team single-elimination core -- same shape regardless of play-in count."""
    rows = []
    for region in REGIONS:
        for i in range(1, 9):
            rows.append(
                {
                    "Season": season,
                    "Slot": f"R1{region}{i}",
                    "StrongSeed": f"{region}{i:02d}",
                    "WeakSeed": f"{region}{17 - i:02d}",
                }
            )
    for region in REGIONS:
        for i in range(1, 5):
            rows.append(
                {
                    "Season": season,
                    "Slot": f"R2{region}{i}",
                    "StrongSeed": f"R1{region}{i}",
                    "WeakSeed": f"R1{region}{9 - i}",
                }
            )
    for region in REGIONS:
        for i in range(1, 3):
            rows.append(
                {
                    "Season": season,
                    "Slot": f"R3{region}{i}",
                    "StrongSeed": f"R2{region}{i}",
                    "WeakSeed": f"R2{region}{5 - i}",
                }
            )
    for region in REGIONS:
        rows.append(
            {
                "Season": season,
                "Slot": f"R4{region}1",
                "StrongSeed": f"R3{region}1",
                "WeakSeed": f"R3{region}2",
            }
        )
    rows.append({"Season": season, "Slot": "R5WX", "StrongSeed": "R4W1", "WeakSeed": "R4X1"})
    rows.append({"Season": season, "Slot": "R5YZ", "StrongSeed": "R4Y1", "WeakSeed": "R4Z1"})
    rows.append({"Season": season, "Slot": "R6CH", "StrongSeed": "R5WX", "WeakSeed": "R5YZ"})
    return rows


def build_synthetic_slots(season: int, play_in_slots: list[str]) -> pd.DataFrame:
    """Mirrors Kaggle's raw file exactly: main-bracket rows first, play-in rows appended last."""
    rows = build_main_bracket_rows(season)
    for code in play_in_slots:
        rows.append(
            {"Season": season, "Slot": code, "StrongSeed": f"{code}a", "WeakSeed": f"{code}b"}
        )
    return pd.DataFrame(rows)


CURRENT_PLAY_IN = ["W16", "X16", "Y10", "Z10"]
EXPANDED_PLAY_IN = ["W16", "W11", "W12", "X16", "X11", "X12", "Y16", "Y11", "Y12", "Z16", "Z11", "Z12"]


def test_current_format_config_is_valid():
    bracket = BracketConfig(size=68, num_rounds=6, num_play_in_games=4)
    validate_bracket_config(bracket)  # does not raise


def test_expanded_76_team_format_config_is_valid():
    bracket = BracketConfig(size=76, num_rounds=6, num_play_in_games=12)
    validate_bracket_config(bracket)  # does not raise


def test_mismatched_size_and_play_in_count_is_rejected():
    bracket = BracketConfig(size=68, num_rounds=6, num_play_in_games=12)
    with pytest.raises(ValueError):
        validate_bracket_config(bracket)


def test_wrong_num_rounds_is_rejected():
    bracket = BracketConfig(size=68, num_rounds=7, num_play_in_games=4)
    with pytest.raises(ValueError):
        validate_bracket_config(bracket)


@pytest.mark.parametrize(
    ("slot", "expected_round", "expected_name"),
    [
        ("R1W1", "R1", "Round of 32"),
        ("R2X3", "R2", "Sweet Sixteen"),
        ("R3Y2", "R3", "Elite Eight"),
        ("R4Z1", "R4", "Final Four"),
        ("R5WX", "R5", "Championship Game"),
        ("R6CH", "R6", "Champion"),
    ],
)
def test_round_classification_of_main_bracket_slots(slot, expected_round, expected_name):
    assert round_of(slot) == expected_round
    assert round_name(slot) == expected_name
    assert not is_play_in_slot(slot)


@pytest.mark.parametrize("slot", ["W16", "X16", "Y10", "Z10"])
def test_play_in_slots_are_classified_correctly(slot):
    assert is_play_in_slot(slot)
    assert round_of(slot) is None
    assert round_name(slot) == "Play-In"


def test_seed_codes_with_letter_suffix_are_not_play_in_slots():
    # "X16a"/"X16b" are seed codes (only ever appear as Strong/WeakSeed), never Slot values.
    assert not is_play_in_slot("X16a")


@pytest.mark.parametrize(
    ("num_play_in_games", "play_in_slots"),
    [(4, CURRENT_PLAY_IN), (12, EXPANDED_PLAY_IN)],
)
def test_expected_slot_count_matches_synthetic_data(num_play_in_games, play_in_slots):
    bracket = BracketConfig(size=MAIN_BRACKET_SIZE + num_play_in_games, num_rounds=6, num_play_in_games=num_play_in_games)
    slots = build_synthetic_slots(2026, play_in_slots)

    assert len(slots) == expected_slot_count(bracket)
    validate_slots(slots, bracket)  # does not raise


def test_validate_slots_rejects_wrong_play_in_count():
    bracket = BracketConfig(size=68, num_rounds=6, num_play_in_games=4)
    slots = build_synthetic_slots(2026, CURRENT_PLAY_IN[:3])  # only 3, not 4

    with pytest.raises(ValueError):
        validate_slots(slots, bracket)


def test_order_slots_for_simulation_resolves_play_in_before_round_one():
    bracket = BracketConfig(size=68, num_rounds=6, num_play_in_games=4)
    raw = build_synthetic_slots(2026, CURRENT_PLAY_IN)  # play-in rows appended last, like real Kaggle files
    assert is_play_in_slot(raw.iloc[-1]["Slot"])  # confirms the fixture mirrors the real quirk

    ordered = order_slots_for_simulation(raw)

    play_in_positions = [i for i, slot in enumerate(ordered["Slot"]) if is_play_in_slot(slot)]
    round_one_positions = [i for i, slot in enumerate(ordered["Slot"]) if round_of(slot) == "R1"]
    assert max(play_in_positions) < min(round_one_positions)


def test_order_slots_for_simulation_keeps_rounds_strictly_increasing():
    bracket = BracketConfig(size=68, num_rounds=6, num_play_in_games=4)
    raw = build_synthetic_slots(2026, CURRENT_PLAY_IN)

    ordered = order_slots_for_simulation(raw)

    def sort_value(slot: str) -> int:
        code = round_of(slot)
        return 0 if code is None else int(code[1])

    values = [sort_value(s) for s in ordered["Slot"]]
    assert values == sorted(values)
