"""Survey responses API endpoints for admin access."""
from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import ResponseServiceDep, AttractionAdminUser
from app.models.schemas.response import (
    SurveyResponseDetail,
    SurveyResponseListItem,
    SurveyAnalytics,
    DailyTrendItem,
)
from app.models.schemas.common import PaginatedResponse

router = APIRouter(prefix="/responses", tags=["Responses"])


@router.get("", response_model=PaginatedResponse[SurveyResponseListItem])
async def list_responses(
    current_user: AttractionAdminUser,
    response_service: ResponseServiceDep,
    survey_id: str | None = Query(None, description="Filter by survey ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[SurveyResponseListItem]:
    """
    List survey responses for the current attraction.

    - **survey_id**: Optional filter by specific survey
    """
    skip = (page - 1) * page_size
    responses, total = await response_service.list_responses(
        attraction_id=str(current_user.attraction_id),
        survey_id=survey_id,
        skip=skip,
        limit=page_size,
    )

    items = [SurveyResponseListItem.from_model(r) for r in responses]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/analytics", response_model=SurveyAnalytics)
async def get_analytics(
    current_user: AttractionAdminUser,
    response_service: ResponseServiceDep,
    survey_id: str | None = Query(None, description="Filter by survey ID"),
) -> SurveyAnalytics:
    """
    Get aggregate analytics for responses.

    - Returns tag score averages
    - Returns section score averages
    - Can filter by specific survey
    """
    if survey_id:
        return await response_service.get_survey_analytics(
            survey_id=survey_id,
            attraction_id=str(current_user.attraction_id),
        )
    else:
        return await response_service.get_attraction_analytics(
            attraction_id=str(current_user.attraction_id),
        )


@router.get("/trends", response_model=list[DailyTrendItem])
async def get_daily_trends(
    current_user: AttractionAdminUser,
    response_service: ResponseServiceDep,
    survey_id: str | None = Query(None, description="Filter by survey ID"),
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days if no date range"),
) -> list[DailyTrendItem]:
    """
    Get daily response trends.

    - Returns daily response counts
    - Returns daily tag score averages
    - Can filter by date range or last N days
    """
    return await response_service.get_daily_trend(
        attraction_id=str(current_user.attraction_id),
        survey_id=survey_id,
        start_date=start_date,
        end_date=end_date,
        days=days,
    )


@router.get("/{response_id}", response_model=SurveyResponseDetail)
async def get_response(
    response_id: str,
    current_user: AttractionAdminUser,
    response_service: ResponseServiceDep,
) -> SurveyResponseDetail:
    """Get detailed view of a single response."""
    response = await response_service.get_response(
        response_id=response_id,
        attraction_id=str(current_user.attraction_id),
    )
    return SurveyResponseDetail.from_model(response)
