"""Template management API endpoints."""
import logging
from fastapi import APIRouter, Query
from bson import ObjectId

from app.api.deps import TemplateServiceDep, SuperAdminUser, AnyAdminUser
from app.models.domain import TemplateStatus
from app.models.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListItem,
    SectionCreate,
    SectionUpdate,
    SectionReorderRequest,
    QuestionCreate,
    QuestionUpdate,
)
from app.models.schemas.common import MessageResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=PaginatedResponse[TemplateListItem])
async def list_templates(
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
    status: TemplateStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TemplateListItem]:
    """
    List all templates (Super Admin only).

    - **status**: Filter by template status (draft, published, archived)
    """
    skip = (page - 1) * page_size
    templates, total = await template_service.list_templates(
        status=status, skip=skip, limit=page_size
    )

    items = [TemplateListItem.from_model(t) for t in templates]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/published", response_model=TemplateResponse | None)
async def get_published_template(
    current_user: AnyAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse | None:
    """Get the currently published template."""
    template = await template_service.get_published_template()
    if template:
        return TemplateResponse.from_model(template)
    return None


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    data: TemplateCreate,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """
    Create a new template (Super Admin only).

    - Templates are created in **draft** status
    - Can include initial sections and questions
    """
    # Convert sections to dict format
    sections_data = []
    for section in data.sections:
        questions_data = []
        for q in section.questions:
            q_dict = {
                "_id": ObjectId(),
                "text": q.text,
                "type": q.type.value,
                "tag": q.tag.value,
                "allow_na": q.allow_na,
            }
            if q.config:
                # config is already a dict from the request
                q_dict["config"] = q.config if isinstance(q.config, dict) else q.config.model_dump()
            questions_data.append(q_dict)

        sections_data.append({
            "_id": ObjectId(),
            "title": section.title,
            "weight": section.weight,
            "allow_notes": section.allow_notes,
            "questions": questions_data,
        })

    template = await template_service.create_template(
        title=data.title,
        created_by=str(current_user.id),
        sections=sections_data,
    )
    return TemplateResponse.from_model(template)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Get template by ID (Super Admin only)."""
    template = await template_service.get_template(template_id)
    return TemplateResponse.from_model(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    data: TemplateUpdate,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """
    Update template (Super Admin only).

    - Can only update **draft** templates
    - Only title can be updated (use section/question endpoints for content)
    """
    updates = data.model_dump(exclude_none=True)
    template = await template_service.update_template(template_id, updates)
    return TemplateResponse.from_model(template)


@router.delete("/{template_id}", response_model=MessageResponse)
async def delete_template(
    template_id: str,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> MessageResponse:
    """
    Delete template (Super Admin only).

    - Can only delete **draft** templates
    - Cannot delete templates with associated surveys
    """
    await template_service.delete_template(template_id)
    return MessageResponse(message="Template deleted successfully")


@router.post("/{template_id}/publish", response_model=TemplateResponse)
async def publish_template(
    template_id: str,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """
    Publish template (Super Admin only).

    - Only one template can be published at a time
    - Publishing will archive any currently published template
    - Template must have at least one section with questions
    """
    template = await template_service.publish_template(template_id)
    return TemplateResponse.from_model(template)


@router.post("/{template_id}/archive", response_model=TemplateResponse)
async def archive_template(
    template_id: str,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Archive template (Super Admin only)."""
    template = await template_service.archive_template(template_id)
    return TemplateResponse.from_model(template)


@router.post("/{template_id}/duplicate", response_model=TemplateResponse, status_code=201)
async def duplicate_template(
    template_id: str,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
    new_title: str = Query(..., min_length=1, max_length=200),
) -> TemplateResponse:
    """
    Duplicate template (Super Admin only).

    - Creates a copy of the template in **draft** status
    - All sections and questions are copied
    """
    template = await template_service.duplicate_template(
        template_id=template_id,
        new_title=new_title,
        created_by=str(current_user.id),
    )
    return TemplateResponse.from_model(template)


# Section endpoints
@router.post("/{template_id}/sections", response_model=TemplateResponse, status_code=201)
async def add_section(
    template_id: str,
    data: SectionCreate,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Add section to template (Super Admin only, draft templates only)."""
    # Convert to dict format
    questions_data = []
    for q in data.questions:
        q_dict = {
            "_id": ObjectId(),
            "text": q.text,
            "type": q.type.value,
            "tag": q.tag.value,
            "allow_na": q.allow_na,
        }
        if q.config:
            q_dict["config"] = q.config
        questions_data.append(q_dict)

    section_data = {
        "title": data.title,
        "weight": data.weight,
        "allow_notes": data.allow_notes,
        "questions": questions_data,
    }

    template = await template_service.add_section(template_id, section_data)
    return TemplateResponse.from_model(template)


@router.put("/{template_id}/sections/{section_id}", response_model=TemplateResponse)
async def update_section(
    template_id: str,
    section_id: str,
    data: SectionUpdate,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Update section in template (Super Admin only, draft templates only)."""
    updates = data.model_dump(exclude_none=True)
    template = await template_service.update_section(template_id, section_id, updates)
    return TemplateResponse.from_model(template)


@router.delete("/{template_id}/sections/{section_id}", response_model=TemplateResponse)
async def remove_section(
    template_id: str,
    section_id: str,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Remove section from template (Super Admin only, draft templates only)."""
    template = await template_service.remove_section(template_id, section_id)
    return TemplateResponse.from_model(template)


@router.put("/{template_id}/sections/reorder", response_model=TemplateResponse)
async def reorder_sections(
    template_id: str,
    data: SectionReorderRequest,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Reorder sections in template (Super Admin only, draft templates only)."""
    template = await template_service.reorder_sections(template_id, data.section_ids)
    return TemplateResponse.from_model(template)


# Question endpoints
@router.post(
    "/{template_id}/sections/{section_id}/questions",
    response_model=TemplateResponse,
    status_code=201,
)
async def add_question(
    template_id: str,
    section_id: str,
    data: QuestionCreate,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Add question to section (Super Admin only, draft templates only)."""
    logger.info(f"add_question called with data: {data.model_dump()}")
    question_data = {
        "text": data.text,
        "type": data.type.value,
        "tag": data.tag.value,
        "allow_na": data.allow_na,
    }
    if data.config:
        question_data["config"] = data.config

    template = await template_service.add_question(template_id, section_id, question_data)
    return TemplateResponse.from_model(template)


@router.put(
    "/{template_id}/sections/{section_id}/questions/{question_id}",
    response_model=TemplateResponse,
)
async def update_question(
    template_id: str,
    section_id: str,
    question_id: str,
    data: QuestionUpdate,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Update question in section (Super Admin only, draft templates only)."""
    updates = {}
    if data.text is not None:
        updates["text"] = data.text
    if data.type is not None:
        updates["type"] = data.type.value
    if data.tag is not None:
        updates["tag"] = data.tag.value
    if data.allow_na is not None:
        updates["allow_na"] = data.allow_na
    if data.config is not None:
        updates["config"] = data.config

    template = await template_service.update_question(
        template_id, section_id, question_id, updates
    )
    return TemplateResponse.from_model(template)


@router.delete(
    "/{template_id}/sections/{section_id}/questions/{question_id}",
    response_model=TemplateResponse,
)
async def remove_question(
    template_id: str,
    section_id: str,
    question_id: str,
    current_user: SuperAdminUser,
    template_service: TemplateServiceDep,
) -> TemplateResponse:
    """Remove question from section (Super Admin only, draft templates only)."""
    template = await template_service.remove_question(template_id, section_id, question_id)
    return TemplateResponse.from_model(template)
