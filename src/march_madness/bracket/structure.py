"""
Bracket structure for the NCAA tournament's 64-team single-elimination core
(Rounds R1-R6), matching Kaggle's MNCAATourneySlots.csv schema exactly. That
64-team, 6-round shape is fixed and does not change with field expansion --
only the number of play-in games feeding into it does. See AGENTS.md
"Fragile Areas" for the play-in slot ordering quirk this module works around.
"""

from __future__ import annotations

import re

import pandas as pd

from march_madness.config import BracketConfig

MAIN_BRACKET_SIZE = 64
MAIN_BRACKET_ROUNDS = 6

# Ported from the legacy project's round_dict -- describes the round each
# code's winners advance TO, matching how the old round-count analysis read it.
ROUND_NAMES = {
    "R1": "Round of 32",
    "R2": "Sweet Sixteen",
    "R3": "Elite Eight",
    "R4": "Final Four",
    "R5": "Championship Game",
    "R6": "Champion",
}

_MAIN_BRACKET_SLOT_RE = re.compile(r"^R([1-6])")
# Play-in slots are a bare region letter + 2-digit seed number (e.g. "X16"),
# distinct from the seed codes with an a/b suffix ("X16a") that only ever
# appear as a play-in slot's StrongSeed/WeakSeed, never as a Slot value.
_PLAY_IN_SLOT_RE = re.compile(r"^[WXYZ]\d{2}$")


def validate_bracket_config(bracket: BracketConfig) -> None:
    """
    Inputs: a BracketConfig (season.yaml's bracket block).
    Outputs: None; raises ValueError on an inconsistent config.
    Purpose: the 64-team, 6-round main bracket is fixed by Kaggle's data
             format. Only the play-in game count changes the total field
             size, so this enforces size == 64 + num_play_in_games instead
             of letting the two config fields silently drift out of sync.
    """
    if bracket.num_rounds != MAIN_BRACKET_ROUNDS:
        raise ValueError(
            f"bracket.num_rounds must be {MAIN_BRACKET_ROUNDS} (the main bracket's round "
            f"count is fixed by Kaggle's data format), got {bracket.num_rounds}"
        )
    expected_size = MAIN_BRACKET_SIZE + bracket.num_play_in_games
    if bracket.size != expected_size:
        raise ValueError(
            f"bracket.size ({bracket.size}) must equal {MAIN_BRACKET_SIZE} + "
            f"num_play_in_games ({bracket.num_play_in_games}) = {expected_size}"
        )


def is_play_in_slot(slot: str) -> bool:
    """True for a play-in slot (e.g. 'X16'), false for a main-bracket round slot (e.g. 'R1X1')."""
    return bool(_PLAY_IN_SLOT_RE.match(slot))


def round_of(slot: str) -> str | None:
    """Round code ('R1'..'R6') a main-bracket slot belongs to, or None for a play-in slot."""
    match = _MAIN_BRACKET_SLOT_RE.match(slot)
    return f"R{match.group(1)}" if match else None


def round_name(slot: str) -> str:
    """Human-readable round name for a slot, e.g. 'R2W1' -> 'Sweet Sixteen'; a play-in slot -> 'Play-In'."""
    code = round_of(slot)
    return ROUND_NAMES[code] if code else "Play-In"


def order_slots_for_simulation(slots: pd.DataFrame) -> pd.DataFrame:
    """
    Inputs: one season's slots, in Kaggle's raw (Season, Slot, StrongSeed,
            WeakSeed) schema/column order.
    Outputs: the same rows, reordered so every slot comes after any other
             slot it references as a Strong/WeakSeed.
    Purpose: Kaggle's raw file lists play-in slots (e.g. 'X16') AFTER the R1
             rows that reference them as a WeakSeed. A simulator that
             resolves each slot's winner while iterating in raw file order
             (as the legacy simulator did, with no sort) would look up an
             unresolved seed for any R1 slot involving a play-in team.
             Play-in slots must always resolve first, then R1..R6 in order.
    """

    def sort_key(slot: str) -> int:
        code = round_of(slot)
        return 0 if code is None else int(code[1])

    return (
        slots.assign(_order=slots["Slot"].map(sort_key))
        .sort_values("_order", kind="stable")
        .drop(columns="_order")
        .reset_index(drop=True)
    )


def expected_slot_count(bracket: BracketConfig) -> int:
    """Total slot rows expected for one season: 63 main-bracket games + N play-in games."""
    main_bracket_games = MAIN_BRACKET_SIZE - 1  # single elimination: N teams -> N-1 games
    return main_bracket_games + bracket.num_play_in_games


def validate_slots(slots: pd.DataFrame, bracket: BracketConfig) -> None:
    """
    Inputs: one season's slots DataFrame and that season's BracketConfig.
    Outputs: None; raises ValueError if the data doesn't match what's configured.
    Purpose: catches a stale/wrong-year slots file, or a config that no
             longer matches reality (e.g. the season had a different number
             of play-in games than config says), before it silently produces
             a broken bracket.
    """
    validate_bracket_config(bracket)

    actual_play_in = int(slots["Slot"].map(is_play_in_slot).sum())
    if actual_play_in != bracket.num_play_in_games:
        raise ValueError(
            f"Expected {bracket.num_play_in_games} play-in slots, found {actual_play_in} in the data"
        )

    actual_total = len(slots)
    expected_total = expected_slot_count(bracket)
    if actual_total != expected_total:
        raise ValueError(
            f"Expected {expected_total} total slots ({MAIN_BRACKET_SIZE - 1} main-bracket + "
            f"{bracket.num_play_in_games} play-in), found {actual_total}"
        )
