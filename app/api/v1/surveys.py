"""Survey management API endpoints."""
from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import (
    SurveyServiceDep,
    AttractionAdminUser,
    SubscribedUser,
    ResponseServiceDep,
)
from app.models.domain import SurveyStatus
from app.models.schemas.survey import (
    SurveyCreate,
    SurveyUpdate,
    SurveyResponse,
    SurveyListItem,
)
from app.models.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/surveys", tags=["Surveys"])


@router.get("", response_model=PaginatedResponse[SurveyListItem])
async def list_surveys(
    current_user: AttractionAdminUser,
    survey_service: SurveyServiceDep,
    response_service: ResponseServiceDep,
    status: SurveyStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[SurveyListItem]:
    """
    List surveys for the current attraction admin.

    - **status**: Filter by survey status (draft, published, archived)
    """
    skip = (page - 1) * page_size
    surveys, total = await survey_service.list_surveys(
        attraction_id=str(current_user.attraction_id),
        status=status,
        skip=skip,
        limit=page_size,
    )

    # Fetch response counts for each survey
    items = []
    for survey in surveys:
        response_count = await response_service.response_repo.count_by_survey(str(survey.id))
        items.append(SurveyListItem.from_model(survey, response_count=response_count))
    
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("", response_model=SurveyResponse, status_code=201)
async def create_survey(
    data: SurveyCreate,
    current_user: SubscribedUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """
    Create a new survey from the published template.

    - Requires active subscription
    - Survey is created in **draft** status
    - Automatically copies sections from the published template
    """
    survey = await survey_service.create_survey(
        attraction_id=str(current_user.attraction_id),
        name=data.name,
    )
    return SurveyResponse.from_model(survey)


@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_survey(
    survey_id: str,
    current_user: AttractionAdminUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """Get survey by ID (must belong to current attraction)."""
    survey = await survey_service.get_survey(
        survey_id=survey_id,
        attraction_id=str(current_user.attraction_id),
    )
    return SurveyResponse.from_model(survey)


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: str,
    data: SurveyUpdate,
    current_user: AttractionAdminUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """
    Update survey (must be in draft status).

    - Can only update name
    - Use publish endpoint to make survey live
    """
    updates = data.model_dump(exclude_none=True)
    survey = await survey_service.update_survey(
        survey_id=survey_id,
        attraction_id=str(current_user.attraction_id),
        updates=updates,
    )
    return SurveyResponse.from_model(survey)


@router.delete("/{survey_id}", response_model=MessageResponse)
async def delete_survey(
    survey_id: str,
    current_user: AttractionAdminUser,
    survey_service: SurveyServiceDep,
) -> MessageResponse:
    """
    Delete survey (must be in draft status).

    - Cannot delete surveys with submitted responses
    """
    await survey_service.delete_survey(
        survey_id=survey_id,
        attraction_id=str(current_user.attraction_id),
    )
    return MessageResponse(message="Survey deleted successfully")


@router.post("/{survey_id}/publish", response_model=SurveyResponse)
async def publish_survey(
    survey_id: str,
    current_user: SubscribedUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """
    Publish survey to make it available for responses.

    - Requires active subscription
    - Only one survey can be published per attraction at a time
    - Publishing will archive any currently published survey
    - Generates QR code for sharing
    """
    survey = await survey_service.publish_survey(
        survey_id=survey_id,
        attraction_id=str(current_user.attraction_id),
    )
    return SurveyResponse.from_model(survey)


@router.post("/{survey_id}/archive", response_model=SurveyResponse)
async def archive_survey(
    survey_id: str,
    current_user: AttractionAdminUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """Archive survey (stops accepting responses)."""
    survey = await survey_service.archive_survey(
        survey_id=survey_id,
        attraction_id=str(current_user.attraction_id),
    )
    return SurveyResponse.from_model(survey)


@router.get("/{survey_id}/qr-code")
async def get_qr_code(
    survey_id: str,
    current_user: AttractionAdminUser,
    survey_service: SurveyServiceDep,
) -> Response:
    """
    Get QR code image for the survey.

    Returns PNG image that links to the public survey URL.
    """
    qr_bytes = await survey_service.get_qr_code(
        survey_id=survey_id,
        attraction_id=str(current_user.attraction_id),
    )
    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename=survey-{survey_id}-qr.png"
        },
    )


@router.get("/{survey_id}/public-url", response_model=dict)
async def get_public_url(
    survey_id: str,
    current_user: AttractionAdminUser,
    survey_service: SurveyServiceDep,
) -> dict:
    """Get the public URL for the survey."""
    survey = await survey_service.get_survey(
        survey_id=survey_id,
        attraction_id=str(current_user.attraction_id),
    )
    public_url = survey_service.get_public_url(survey.share_id)
    return {"url": public_url, "share_id": survey.share_id}
