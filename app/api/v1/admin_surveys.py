"""Super Admin survey management API endpoints."""
from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import (
    SurveyServiceDep,
    SuperAdminUser,
    ResponseServiceDep,
    DatabaseDep,
    TemplateRepoDep,
)
from app.models.domain import SurveyStatus
from app.models.schemas.survey import (
    SurveyUpdate,
    SurveyResponse,
    SurveyListItem,
)
from app.models.schemas.common import MessageResponse, PaginatedResponse
from bson import ObjectId

router = APIRouter(prefix="/admin/surveys", tags=["Admin Surveys"])


@router.get("", response_model=PaginatedResponse[SurveyListItem])
async def list_all_surveys(
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
    response_service: ResponseServiceDep,
    template_repo: TemplateRepoDep,
    db: DatabaseDep,
    status: SurveyStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[SurveyListItem]:
    """
    List all surveys across all attractions (Super Admin only).

    - **status**: Filter by survey status (draft, published, archived)
    """
    skip = (page - 1) * page_size
    surveys, total = await survey_service.list_surveys(
        attraction_id=None,  # None means all attractions
        status=status,
        skip=skip,
        limit=page_size,
    )

    # Fetch response counts and enrich with attraction/template names
    items = []
    for survey in surveys:
        response_count = await response_service.response_repo.count_by_survey(str(survey.id))
        
        # Get attraction name
        attraction_name = None
        if survey.attraction_id:
            attraction = await db["attractions"].find_one({"_id": survey.attraction_id})
            if attraction:
                attraction_name = attraction.get("name")
        
        # Get template name
        template_name = None
        if survey.template_id:
            template = await template_repo.find_by_id(str(survey.template_id))
            if template:
                template_name = template.title  # Template uses 'title' not 'name'
        
        items.append(SurveyListItem.from_model(
            survey, 
            response_count=response_count,
            attraction_name=attraction_name,
            template_name=template_name
        ))
    
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_any_survey(
    survey_id: str,
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """Get any survey by ID (Super Admin only)."""
    survey = await survey_service.get_survey(
        survey_id=survey_id,
        attraction_id=None,  # None means no ownership check
    )
    return SurveyResponse.from_model(survey)


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_any_survey(
    survey_id: str,
    data: SurveyUpdate,
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """
    Update any survey (Super Admin only).

    - Can update regardless of status
    - No ownership checks
    """
    # Get the survey first to get its attraction_id
    survey = await survey_service.get_survey(survey_id=survey_id, attraction_id=None)
    
    updates = data.model_dump(exclude_none=True)
    updated_survey = await survey_service.update_survey(
        survey_id=survey_id,
        attraction_id=str(survey.attraction_id),
        updates=updates,
    )
    return SurveyResponse.from_model(updated_survey)


@router.delete("/{survey_id}", response_model=MessageResponse)
async def delete_any_survey(
    survey_id: str,
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
) -> MessageResponse:
    """
    Delete any survey (Super Admin only).

    - Can delete regardless of status
    - No ownership checks
    """
    # Get the survey first to get its attraction_id
    survey = await survey_service.get_survey(survey_id=survey_id, attraction_id=None)
    
    await survey_service.delete_survey(
        survey_id=survey_id,
        attraction_id=str(survey.attraction_id),
    )
    return MessageResponse(message="Survey deleted successfully")


@router.post("/{survey_id}/publish", response_model=SurveyResponse)
async def publish_any_survey(
    survey_id: str,
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """
    Publish any survey (Super Admin only).

    - Publishing will archive any currently published survey for that attraction
    """
    # Get the survey first to get its attraction_id
    survey = await survey_service.get_survey(survey_id=survey_id, attraction_id=None)
    
    published_survey = await survey_service.publish_survey(
        survey_id=survey_id,
        attraction_id=str(survey.attraction_id),
    )
    return SurveyResponse.from_model(published_survey)


@router.post("/{survey_id}/archive", response_model=SurveyResponse)
async def archive_any_survey(
    survey_id: str,
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
) -> SurveyResponse:
    """Archive any survey (Super Admin only)."""
    # Get the survey first to get its attraction_id
    survey = await survey_service.get_survey(survey_id=survey_id, attraction_id=None)
    
    archived_survey = await survey_service.archive_survey(
        survey_id=survey_id,
        attraction_id=str(survey.attraction_id),
    )
    return SurveyResponse.from_model(archived_survey)


@router.get("/{survey_id}/qr-code")
async def get_any_qr_code(
    survey_id: str,
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
) -> Response:
    """
    Get QR code image for any survey (Super Admin only).

    Returns PNG image that links to the public survey URL.
    """
    # Get the survey first to get its attraction_id
    survey = await survey_service.get_survey(survey_id=survey_id, attraction_id=None)
    
    qr_bytes = await survey_service.get_qr_code(
        survey_id=survey_id,
        attraction_id=str(survey.attraction_id),
    )
    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename=survey-{survey_id}-qr.png"
        },
    )


@router.get("/{survey_id}/public-url", response_model=dict)
async def get_any_public_url(
    survey_id: str,
    current_user: SuperAdminUser,
    survey_service: SurveyServiceDep,
) -> dict:
    """Get the public URL for any survey (Super Admin only)."""
    survey = await survey_service.get_survey(
        survey_id=survey_id,
        attraction_id=None,
    )
    public_url = survey_service.get_public_url(survey.share_id)
    return {"url": public_url, "share_id": survey.share_id}
