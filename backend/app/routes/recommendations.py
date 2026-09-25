from fastapi import APIRouter

from app.services.recommendations import get_recommendations

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", summary="Get data-backed civic recommendations")
async def recommendations():
    return await get_recommendations()
