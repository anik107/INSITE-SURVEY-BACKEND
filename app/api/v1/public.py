"""Public survey API endpoints (no authentication required)."""
from fastapi import APIRouter, Request

from app.api.deps import ResponseServiceDep
from app.models.schemas.survey import PublicSurveyResponse
from app.models.schemas.response import ResponseSubmit, ResponseSubmitResult

router = APIRouter(prefix="/public", tags=["Public Surveys"])


@router.get("/surveys/{share_id}", response_model=PublicSurveyResponse)
async def get_public_survey(
    share_id: str,
    response_service: ResponseServiceDep,
) -> PublicSurveyResponse:
    """
    Get public survey for visitors to fill.

    - Only returns published surveys
    - Does not require authentication
    - Uses share_id slug instead of internal ID
    """
    return await response_service.get_public_survey(share_id)


@router.post(
    "/surveys/{share_id}/responses",
    response_model=ResponseSubmitResult,
    status_code=201,
)
async def submit_response(
    share_id: str,
    data: ResponseSubmit,
    request: Request,
    response_service: ResponseServiceDep,
) -> ResponseSubmitResult:
    """
    Submit survey response.

    - Does not require authentication
    - Validates all required questions are answered
    - Calculates scores automatically
    - Prevents duplicate submissions (12-hour window based on fingerprint)
    """
    # Get client IP for duplicate detection fallback
    client_ip = request.client.host if request.client else None

    return await response_service.submit_response(
        share_id=share_id,
        data=data,
        fingerprint=data.fingerprint,
        client_ip=client_ip,
    )
