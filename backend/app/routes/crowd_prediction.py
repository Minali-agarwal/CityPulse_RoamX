from fastapi import APIRouter, HTTPException, status

from app.models.crowd_prediction import CrowdPredictionRequest, CrowdPredictionResponse
from app.services.crowd_prediction import (
    PredictionUnavailableError,
    crowd_prediction_service,
)


router = APIRouter(prefix="/predictions", tags=["ML Predictions"])


@router.post(
    "/crowd",
    response_model=CrowdPredictionResponse,
    summary="Predict crowd level for a city zone and time",
    description=(
        "Uses the saved CityPulse crowd classifier and fitted preprocessing artifacts. "
        "Numeric and weather-condition measurements may be omitted and are imputed "
        "using training-set statistics."
    ),
)
def predict_crowd(payload: CrowdPredictionRequest) -> CrowdPredictionResponse:
    try:
        return CrowdPredictionResponse(**crowd_prediction_service.predict(payload))
    except PredictionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Crowd prediction is unavailable: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crowd prediction failed: {exc}",
        ) from exc
