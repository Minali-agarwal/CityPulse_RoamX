"""Train and evaluate a baseline CityPulse crowd-level classifier."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from ml.data_pipeline import CROWD_LEVELS, load_dataset, prepare_dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def train(dataset_path: str | Path, artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR) -> dict:
    """Train on the real labeled CSV and persist estimator/preprocessor artifacts."""

    dataset = Path(dataset_path).expanduser()
    if not dataset.is_absolute():
        dataset = (PROJECT_ROOT / dataset).resolve()
    if not dataset.is_file():
        raise FileNotFoundError(
            f"Labeled dataset not found: {dataset}\n"
            "Add verified crowd observations at ml/data/crowd_observations.csv. "
            "Do not use the *_TEMPLATE_DEV_ONLY.csv file for training."
        )

    try:
        records = load_dataset(dataset)
        split = prepare_dataset(records)
    except (ValueError, OSError, UnicodeError) as exc:
        raise ValueError(f"Dataset validation/preprocessing failed: {exc}") from exc

    labels_in_train = set(split.y_train.astype(str))
    if len(labels_in_train) < 2:
        raise ValueError(
            "The chronological training partition contains fewer than two crowd_level classes. "
            "Provide more verified labeled observations across time."
        )
    if len(split.y_test) == 0:
        raise ValueError("The chronological test partition is empty; provide more observations.")

    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(split.X_train, split.y_train)
    predictions = model.predict(split.X_test)

    metrics = {
        "accuracy": float(accuracy_score(split.y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(split.y_test, predictions)),
        "precision_macro": float(
            precision_score(split.y_test, predictions, labels=list(CROWD_LEVELS), average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(split.y_test, predictions, labels=list(CROWD_LEVELS), average="macro", zero_division=0)
        ),
        "f1_macro": float(
            f1_score(split.y_test, predictions, labels=list(CROWD_LEVELS), average="macro", zero_division=0)
        ),
        "classification_report": classification_report(
            split.y_test,
            predictions,
            labels=list(CROWD_LEVELS),
            target_names=list(CROWD_LEVELS),
            zero_division=0,
            output_dict=True,
        ),
        "confusion_matrix_labels": list(CROWD_LEVELS),
        "confusion_matrix": confusion_matrix(
            split.y_test, predictions, labels=list(CROWD_LEVELS)
        ).tolist(),
    }

    output_dir = Path(artifact_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (PROJECT_ROOT / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Keep artifacts distinct so inference can reuse the exact fitted transforms.
    joblib.dump(model, output_dir / "crowd_level_model.joblib")
    joblib.dump(split.preprocessor, output_dir / "crowd_level_preprocessor.joblib")
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset),
        "model": "LogisticRegression",
        "target": "crowd_level",
        "classes": [str(label) for label in model.classes_],
        "train_rows": int(len(split.y_train)),
        "test_rows": int(len(split.y_test)),
        "train_start_utc": split.train_timestamps.min().isoformat(),
        "train_end_utc": split.train_timestamps.max().isoformat(),
        "test_start_utc": split.test_timestamps.min().isoformat(),
        "test_end_utc": split.test_timestamps.max().isoformat(),
        "metrics": metrics,
    }
    (output_dir / "training_metrics.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    print(f"Dataset: {dataset}")
    print(f"Rows: {len(records)} (train {len(split.y_train)}, test {len(split.y_test)})")
    print("Model: LogisticRegression(class_weight='balanced')")
    print("Evaluation metrics:")
    for name in ("accuracy", "balanced_accuracy", "precision_macro", "recall_macro", "f1_macro"):
        print(f"  {name}: {metrics[name]:.4f}")
    print("\nPer-class report:")
    for label in CROWD_LEVELS:
        row = metrics["classification_report"][label]
        print(
            f"  {label}: precision={row['precision']:.4f}, "
            f"recall={row['recall']:.4f}, f1={row['f1-score']:.4f}, support={int(row['support'])}"
        )
    print("\nConfusion matrix (rows=true, columns=predicted; labels low, moderate, high):")
    for row in metrics["confusion_matrix"]:
        print("  " + " ".join(str(value) for value in row))
    print(f"\nSaved model, preprocessor, and metrics under: {output_dir}")
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and evaluate a baseline crowd-level classifier from verified labeled data."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the real labeled CSV (for example: ml/data/crowd_observations.csv)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        train(args.dataset)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Training not completed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
