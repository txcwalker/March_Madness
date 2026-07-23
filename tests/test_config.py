from pathlib import Path

import pytest
import yaml

from march_madness.config import REPO_ROOT, load_season_config


def write_config(tmp_path: Path, **overrides) -> Path:
    payload = {
        "year": 2026,
        "bracket": {"size": 68, "num_rounds": 6, "num_play_in_games": 4},
    }
    payload.update(overrides)
    config_path = tmp_path / "season.yaml"
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config_path


def test_loads_year_and_bracket_settings(tmp_path):
    config = load_season_config(write_config(tmp_path))

    assert config.year == 2026
    assert config.bracket.size == 68
    assert config.bracket.num_rounds == 6
    assert config.bracket.num_play_in_games == 4


def test_derives_per_year_data_paths(tmp_path):
    config = load_season_config(write_config(tmp_path))

    assert config.raw_dir == REPO_ROOT / "data" / "raw" / "2026"
    assert config.processed_dir == REPO_ROOT / "data" / "processed" / "2026"
    assert config.outputs_dir == REPO_ROOT / "data" / "outputs" / "2026"


def test_different_years_produce_different_paths(tmp_path):
    config_2025 = load_season_config(write_config(tmp_path, year=2025))
    config_2026 = load_season_config(write_config(tmp_path, year=2026))

    assert config_2025.raw_dir != config_2026.raw_dir
    assert config_2025.year == 2025


@pytest.mark.parametrize(
    "bracket_overrides",
    [
        {"size": 0, "num_rounds": 6, "num_play_in_games": 4},
        {"size": 68, "num_rounds": 0, "num_play_in_games": 4},
        {"size": 68, "num_rounds": 6, "num_play_in_games": -1},
    ],
)
def test_rejects_invalid_bracket_settings(tmp_path, bracket_overrides):
    config_path = write_config(tmp_path, bracket=bracket_overrides)

    with pytest.raises(ValueError):
        load_season_config(config_path)


def test_ensure_data_dirs_creates_processed_and_outputs_but_not_raw(tmp_path, monkeypatch):
    import march_madness.config as config_module

    fake_root = tmp_path / "repo"
    monkeypatch.setattr(config_module, "REPO_ROOT", fake_root)

    config_path = write_config(tmp_path, year=2099)
    config = load_season_config(config_path)
    config.ensure_data_dirs()

    assert config.processed_dir.is_dir()
    assert config.outputs_dir.is_dir()
    assert not config.raw_dir.exists()
