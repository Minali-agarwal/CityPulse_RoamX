import logging
import math
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

from app.models.crowd_prediction import CrowdPredictionRequest


logger = logging.getLogger("citypulse.ml.crowd_prediction")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = PROJECT_ROOT / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "crowd_level_model.joblib"
PREPROCESSOR_PATH = ARTIFACT_DIR / "crowd_level_preprocessor.joblib"


class PredictionUnavailableError(RuntimeError):
    """Raised when the persisted model artifacts are not available or loadable."""


class CrowdPredictionService:
    def __init__(self, model_path: Path = MODEL_PATH, preprocessor_path: Path = PREPROCESSOR_PATH):
        self.model_path = Path(model_path)
        self.preprocessor_path = Path(preprocessor_path)
        self.model: Optional[Any] = None
        self.preprocessor: Optional[Any] = None
        self.load_error: Optional[str] = None
        self._loaded = False

    def load(self) -> bool:
        """Load artifacts once during FastAPI startup; never train or synthesize a model."""

        if self._loaded:
            return self.model is not None and self.preprocessor is not None
        self._loaded = True
        missing = [str(path) for path in (self.model_path, self.preprocessor_path) if not path.is_file()]
        if missing:
            self.load_error = "Required crowd model artifact(s) are missing: " + ", ".join(missing)
            logger.warning(self.load_error)
            return False

        try:
            model = joblib.load(self.model_path)
            preprocessor = joblib.load(self.preprocessor_path)
            if not callable(getattr(model, "predict", None)):
                raise TypeError("Saved model does not provide predict().")
            if not callable(getattr(preprocessor, "transform", None)):
                raise TypeError("Saved preprocessor does not provide transform().")
            if not hasattr(model, "classes_") or not hasattr(preprocessor, "feature_names_in_"):
                raise TypeError("Saved artifacts are missing fitted class or feature metadata.")
            self.model = model
            self.preprocessor = preprocessor
            logger.info("Loaded crowd model and preprocessor from %s", ARTIFACT_DIR)
            return True
        except Exception as exc:
            self.model = None
            self.preprocessor = None
            self.load_error = f"Could not load crowd model artifacts: {exc}"
            logger.exception(self.load_error)
            return False

    @staticmethod
    def _feature_row(payload: CrowdPredictionRequest) -> pd.DataFrame:
        local_timestamp = pd.Timestamp(payload.timestamp).tz_convert("Asia/Kolkata")
        hour = local_timestamp.hour + local_timestamp.minute / 60.0
        weekday = local_timestamp.dayofweek
        row: Dict[str, Any] = {
            "temperature_c": payload.temperature_c,
            "rainfall_mm": payload.rainfall_mm,
            "humidity_pct": payload.humidity_pct,
            "wind_speed_kmh": payload.wind_speed_kmh,
            "air_quality_index": payload.air_quality_index,
            "congestion_percentage": payload.congestion_percentage,
            "traffic_delay_minutes": payload.traffic_delay_minutes,
            "average_speed_kmh": payload.average_speed_kmh,
            "incident_count": payload.incident_count,
            "active_incident_count": payload.active_incident_count,
            "high_critical_incident_count": payload.high_critical_incident_count,
            "zone": payload.zone,
            "weather_condition": payload.weather_condition,
            "hour_sin": math.sin(2.0 * math.pi * hour / 24.0),
            "hour_cos": math.cos(2.0 * math.pi * hour / 24.0),
            "day_of_week_sin": math.sin(2.0 * math.pi * weekday / 7.0),
            "day_of_week_cos": math.cos(2.0 * math.pi * weekday / 7.0),
        }
        return pd.DataFrame([row])

    def predict(self, payload: CrowdPredictionRequest) -> Dict[str, Any]:
        if self.model is None or self.preprocessor is None:
            detail = self.load_error or "Crowd prediction artifacts are not loaded."
            raise PredictionUnavailableError(detail)

        expected_features = list(self.preprocessor.feature_names_in_)
        features = self._feature_row(payload).reindex(columns=expected_features)
        transformed = self.preprocessor.transform(features)
        crowd_level = str(self.model.predict(transformed)[0])

        probabilities: Dict[str, float] = {}
        if callable(getattr(self.model, "predict_proba", None)):
            values = self.model.predict_proba(transformed)[0]
            probabilities = {
                str(label): float(probability)
                for label, probability in zip(self.model.classes_, values)
            }
            confidence = probabilities.get(crowd_level, 0.0)
        else:
            confidence = 0.0

        if crowd_level not in {"low", "moderate", "high"}:
            raise RuntimeError(f"Model returned an unsupported crowd_level: {crowd_level}")
        return {
            "crowd_level": crowd_level,
            "confidence": confidence,
            "probabilities": probabilities,
        }


crowd_prediction_service = CrowdPredictionService()
