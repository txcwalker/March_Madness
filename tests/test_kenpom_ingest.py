import pandas as pd
import pytest

from march_madness.ingest.kenpom import build_kenpom_history, clean_kenpom_export

# Mirrors the real kenpom_2026_raw.csv header exactly: Rk, Team, Conf, W-L,
# then NetRtg/ORtg/DRtg/AdjT/Luck each paired with a blank rank-subscript
# column, then the Strength-of-Schedule and Non-Conference-SOS groups.
RAW_HEADER = "Rk,Team,Conf,W-L,NetRtg,ORtg,,DRtg,,AdjT,,Luck,,NetRtg,,ORtg,,DRtg,,NetRtg,\n"
RAW_ROW_DUKE = "1,Duke 1,ACC,32-2,38.9,128,4,89.1,2,65.3,287,0.049,63,14.29,15,117,24,102.7,10,10.07,18\n"
RAW_ROW_ARIZONA = "2,Arizona 1,B12,32-2,37.66,127.7,5,90,3,69.8,54,0.023,127,14.97,9,117.6,15,102.7,7,3.25,102\n"
REPEATED_HEADER_ROW = "Rk,Team,Conf,W-L,NetRtg,ORtg,,DRtg,,AdjT,,Luck,,NetRtg,,ORtg,,DRtg,,NetRtg,\n"
RAW_ROW_NO_SEED = "3,Houston,B12,28-7,35.1,124.3,11,89.2,3,68.1,90,0.01,100,12.1,20,116.2,18,100.9,15,5.4,60\n"
# Excel date-mangles "20-12" into "20-Dec" when the loss count looks like a month number.
RAW_ROW_EXCEL_DATE_MANGLED = "4,Marquette,BE,20-Dec,28.1,119.3,15,91.2,8,66.0,150,0.01,90,10.1,25,114.2,30,104.1,20,2.1,80\n"


def read_raw(text: str) -> pd.DataFrame:
    import io

    return pd.read_csv(io.StringIO(text))


def test_drops_rank_subscript_columns():
    raw = read_raw(RAW_HEADER + RAW_ROW_DUKE)
    cleaned = clean_kenpom_export(raw, season=2026)

    assert not any(col.startswith("Unnamed") for col in cleaned.columns)


def test_renames_duplicate_stat_groups():
    raw = read_raw(RAW_HEADER + RAW_ROW_DUKE)
    cleaned = clean_kenpom_export(raw, season=2026)

    for expected_col in ["NetRtg", "SOS_NetRtg", "NCSOS_NetRtg", "ORtg", "SOS_ORtg", "DRtg", "SOS_DRtg"]:
        assert expected_col in cleaned.columns


def test_drops_stray_repeated_header_row():
    raw = read_raw(RAW_HEADER + RAW_ROW_DUKE + REPEATED_HEADER_ROW + RAW_ROW_ARIZONA)
    cleaned = clean_kenpom_export(raw, season=2026)

    assert len(cleaned) == 2
    assert set(cleaned["Team"]) == {"Duke", "Arizona"}


def test_splits_team_name_and_seed():
    raw = read_raw(RAW_HEADER + RAW_ROW_DUKE)
    cleaned = clean_kenpom_export(raw, season=2026)

    row = cleaned.iloc[0]
    assert row["Team"] == "Duke"
    assert row["Seed"] == 1


def test_team_with_no_seed_digit_has_missing_seed():
    raw = read_raw(RAW_HEADER + RAW_ROW_NO_SEED)
    cleaned = clean_kenpom_export(raw, season=2026)

    row = cleaned.iloc[0]
    assert row["Team"] == "Houston"
    assert pd.isna(row["Seed"])


def test_splits_wins_and_losses():
    raw = read_raw(RAW_HEADER + RAW_ROW_DUKE)
    cleaned = clean_kenpom_export(raw, season=2026)

    row = cleaned.iloc[0]
    assert row["W"] == 32
    assert row["L"] == 2
    assert "W-L" not in cleaned.columns


def test_recovers_losses_excel_mangled_into_a_date():
    raw = read_raw(RAW_HEADER + RAW_ROW_EXCEL_DATE_MANGLED)
    cleaned = clean_kenpom_export(raw, season=2026)

    row = cleaned.iloc[0]
    assert row["W"] == 20
    assert row["L"] == 12  # "20-Dec" -> December -> 12, not NaN


def test_adds_season_column():
    raw = read_raw(RAW_HEADER + RAW_ROW_DUKE)
    cleaned = clean_kenpom_export(raw, season=2026)

    assert (cleaned["Season"] == 2026).all()


def test_build_kenpom_history_merges_multiple_years(tmp_path):
    (tmp_path / "2025").mkdir()
    (tmp_path / "2025" / "kenpom_raw.csv").write_text(RAW_HEADER + RAW_ROW_ARIZONA, encoding="utf-8")
    (tmp_path / "2026").mkdir()
    (tmp_path / "2026" / "kenpom_raw.csv").write_text(RAW_HEADER + RAW_ROW_DUKE, encoding="utf-8")

    history = build_kenpom_history(tmp_path)

    assert list(history["Season"]) == [2025, 2026]
    assert set(history["Team"]) == {"Arizona", "Duke"}


def test_build_kenpom_history_raises_when_nothing_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_kenpom_history(tmp_path)
