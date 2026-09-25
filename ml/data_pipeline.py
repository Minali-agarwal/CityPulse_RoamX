"""Prepare labeled, zone-and-time-window CityPulse data for crowd-level modeling.

This module deliberately stops before estimator/model training. The target must
come from measured or human-labeled crowd observations; it is never inferred
from the UI's current prediction or from the input telemetry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET: Final = "crowd_level"
CROWD_LEVELS: Final = ("low", "moderate", "high")

# Expected one-row-per-zone-per-time-window CSV columns.
REQUIRED_COLUMNS: Final = (
    "timestamp",
    "zone",
    "temperature_c",
    "rainfall_mm",
    "humidity_pct",
    "wind_speed_kmh",
    "air_quality_index",
    "weather_condition",
    "congestion_percentage",
    "traffic_delay_minutes",
    "average_speed_kmh",
    "incident_count",
    "active_incident_count",
    "high_critical_incident_count",
    TARGET,
)

NUMERIC_FEATURES: Final = (
    "temperature_c",
    "rainfall_mm",
    "humidity_pct",
    "wind_speed_kmh",
    "air_quality_index",
    "congestion_percentage",
    "traffic_delay_minutes",
    "average_speed_kmh",
    "incident_count",
    "active_incident_count",
    "high_critical_incident_count",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
)
CATEGORICAL_FEATURES: Final = ("zone", "weather_condition")


@dataclass(frozen=True)
class PreparedSplit:
    """Chronological holdout with features transformed using training rows only."""

    X_train: object
    X_test: object
    y_train: pd.Series
    y_test: pd.Series
    preprocessor: ColumnTransformer
    train_timestamps: pd.Series
    test_timestamps: pd.Series


def load_dataset(path: str | Path) -> pd.DataFrame:
    """Load a labeled CSV and enforce the documented dataset contract."""

    frame = pd.read_csv(path)
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    return validate_dataset(frame)


def validate_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate target, timestamp, and input columns without creating labels."""

    # Development examples must never silently become training labels.
    if "example_only" in frame.columns:
        examples = frame["example_only"].astype("string").str.strip().str.lower()
        if examples.isin({"true", "1", "yes", "y"}).any():
            raise ValueError(
                "Development-only example rows cannot be used as real crowd labels. "
                "Use the curated ml/data/crowd_observations.csv dataset instead."
            )

    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("Dataset has no rows.")

    result = frame.loc[:, list(REQUIRED_COLUMNS)].copy()
    result[TARGET] = result[TARGET].astype("string").str.strip().str.lower()
    if result[TARGET].isna().any() or result[TARGET].eq("").any():
        raise ValueError("Every row must have a measured/labeled crowd_level target.")
    invalid_levels = sorted(set(result[TARGET].dropna()) - set(CROWD_LEVELS))
    if invalid_levels:
        raise ValueError(
            "crowd_level must be one of " + ", ".join(CROWD_LEVELS)
            + "; found: " + ", ".join(invalid_levels)
        )

    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce", utc=True)
    if result["timestamp"].isna().any():
        raise ValueError("Every row must have a valid ISO-8601 timestamp.")
    if result["zone"].isna().any() or result["zone"].astype("string").str.strip().eq("").any():
        raise ValueError("Every row must identify a city zone.")
    return result.sort_values("timestamp", kind="stable").reset_index(drop=True)


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Engineer local Jaipur time cycles and return model inputs only."""

    result = validate_dataset(frame)
    local_time = result["timestamp"].dt.tz_convert("Asia/Kolkata")
    hour = local_time.dt.hour + local_time.dt.minute / 60.0
    weekday = local_time.dt.dayofweek

    features = result.loc[:, [*NUMERIC_FEATURES[:11], *CATEGORICAL_FEATURES]].copy()
    features["hour_sin"] = (2.0 * math.pi * hour / 24.0).map(math.sin)
    features["hour_cos"] = (2.0 * math.pi * hour / 24.0).map(math.cos)
    features["day_of_week_sin"] = (2.0 * math.pi * weekday / 7.0).map(math.sin)
    features["day_of_week_cos"] = (2.0 * math.pi * weekday / 7.0).map(math.cos)
    return features.loc[:, [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]]


def build_preprocessor() -> ColumnTransformer:
    """Create numeric imputation/scaling and categorical imputation/encoding."""

    numeric_pipeline = Pipeline(
        steps=[("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, list(NUMERIC_FEATURES)),
            ("categorical", categorical_pipeline, list(CATEGORICAL_FEATURES)),
        ],
        remainder="drop",
    )


def chronological_split(
    frame: pd.DataFrame, test_fraction: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by timestamp so future observations are held out for testing.

    Rows sharing a timestamp always remain in the same split, preventing
    same-window zone observations from crossing the temporal boundary.
    """

    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be between 0 and 1.")
    data = validate_dataset(frame)
    timestamps = data["timestamp"].drop_duplicates().sort_values().reset_index(drop=True)
    if len(timestamps) < 2:
        raise ValueError("At least two distinct timestamps are required for a chronological split.")
    split_index = min(len(timestamps) - 1, max(1, int(len(timestamps) * (1.0 - test_fraction))))
    cutoff = timestamps.iloc[split_index - 1]
    train = data.loc[data["timestamp"] <= cutoff].copy()
    test = data.loc[data["timestamp"] > cutoff].copy()
    return train.reset_index(drop=True), test.reset_index(drop=True)


def prepare_dataset(frame: pd.DataFrame, test_fraction: float = 0.2) -> PreparedSplit:
    """Validate, chronologically split, and preprocess without training a model."""

    data = validate_dataset(frame)
    train, test = chronological_split(data, test_fraction=test_fraction)
    X_train_raw = build_features(train)
    X_test_raw = build_features(test)
    y_train = train[TARGET].copy()
    y_test = test[TARGET].copy()

    preprocessor = build_preprocessor()
    X_train = preprocessor.fit_transform(X_train_raw)
    X_test = preprocessor.transform(X_test_raw)
    return PreparedSplit(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        preprocessor=preprocessor,
        train_timestamps=train["timestamp"].copy(),
        test_timestamps=test["timestamp"].copy(),
    )
