"""Loads config/season.yaml and exposes season/bracket settings and per-year data paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "season.yaml"


@dataclass(frozen=True)
class BracketConfig:
    size: int
    num_rounds: int
    num_play_in_games: int

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError(f"bracket.size must be positive, got {self.size}")
        if self.num_rounds <= 0:
            raise ValueError(f"bracket.num_rounds must be positive, got {self.num_rounds}")
        if self.num_play_in_games < 0:
            raise ValueError(
                f"bracket.num_play_in_games cannot be negative, got {self.num_play_in_games}"
            )


@dataclass(frozen=True)
class SeasonConfig:
    """
    Inputs: parsed contents of config/season.yaml.
    Outputs: typed season/bracket settings plus this year's data directories,
             consumed by every ingest/feature/model/bracket module.
    Purpose: single source of truth for "which year, which bracket format,
             where does this year's data live" -- replaces the scattered
             hardcoded years and team counts from the legacy project.
    """

    year: int
    bracket: BracketConfig
    raw_dir: Path
    processed_dir: Path
    outputs_dir: Path

    def ensure_data_dirs(self) -> None:
        """Creates this year's processed/outputs directories if they don't exist yet.

        raw_dir is intentionally not created here -- it holds hand-supplied
        input data, and an ingest module should fail clearly if it's missing
        rather than silently operating on an empty directory.
        """
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)


def load_season_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> SeasonConfig:
    """
    Inputs: path to a season YAML file (defaults to config/season.yaml).
    Outputs: a validated SeasonConfig.
    Purpose: parses the YAML and derives this year's data directories
             (data/raw/<year>, data/processed/<year>, data/outputs/<year>)
             under the repo root, so callers never construct a year-specific
             path themselves.
    """
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    year = raw["year"]
    bracket = BracketConfig(**raw["bracket"])

    return SeasonConfig(
        year=year,
        bracket=bracket,
        raw_dir=REPO_ROOT / "data" / "raw" / str(year),
        processed_dir=REPO_ROOT / "data" / "processed" / str(year),
        outputs_dir=REPO_ROOT / "data" / "outputs" / str(year),
    )
