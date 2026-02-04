"""Survey service for business logic."""
import secrets
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.config import settings
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    BusinessRuleError,
    ForbiddenError,
    TemplateNotPublishedError,
)
from app.models.domain import Survey, SurveyStatus, SurveySection
from app.repositories.survey_repository import SurveyRepository
from app.repositories.template_repository import TemplateRepository
from app.utils.qr_generator import generate_survey_qr
from app.core.cache import invalidate_cache


class SurveyService:
    """Service for survey management operations."""

    def __init__(
        self,
        survey_repo: SurveyRepository,
        template_repo: TemplateRepository,
        attraction_collection=None,
    ):
        self.survey_repo = survey_repo
        self.template_repo = template_repo
        self.attraction_collection = attraction_collection

    def _generate_share_id(self) -> str:
        """Generate URL-safe unique share ID."""
        return secrets.token_urlsafe(8)

    async def _ensure_unique_share_id(self) -> str:
        """Generate unique share_id that doesn't exist."""
        max_attempts = 10
        for _ in range(max_attempts):
            share_id = self._generate_share_id()
            if not await self.survey_repo.share_id_exists(share_id):
                return share_id
        raise ValidationError("Failed to generate unique share ID")

    async def list_surveys(
        self,
        attraction_id: str | None = None,
        status: SurveyStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Survey], int]:
        """List surveys with filtering."""
        if attraction_id:
            surveys = await self.survey_repo.find_by_attraction(
                attraction_id, status, skip, limit
            )
            total = await self.survey_repo.count_by_attraction(attraction_id, status)
        else:
            filter = {}
            if status:
                filter["status"] = status.value
            surveys = await self.survey_repo.find_many(
                filter,
                skip=skip,
                limit=limit,
                sort=[("updated_at", -1)],
            )
            total = await self.survey_repo.count(filter)

        return surveys, total

    async def get_survey(
        self,
        survey_id: str,
        attraction_id: str | None = None,
    ) -> Survey:
        """
        Get survey by ID.

        If attraction_id is provided, verifies ownership.
        """
        survey = await self.survey_repo.find_by_id(survey_id)
        if not survey:
            raise NotFoundError("Survey", survey_id)

        if attraction_id and str(survey.attraction_id) != attraction_id:
            raise ForbiddenError("You can only access your own surveys")

        return survey

    async def get_survey_by_share_id(self, share_id: str) -> Survey:
        """Get survey by share_id."""
        survey = await self.survey_repo.find_by_share_id(share_id)
        if not survey:
            raise NotFoundError("Survey", share_id)
        return survey

    async def create_survey(
        self,
        attraction_id: str,
        name: str,
    ) -> Survey:
        """
        Create survey from published template.

        All sections from the published template are included by default.
        """
        # Get published template
        template = await self.template_repo.find_published()
        if not template:
            raise TemplateNotPublishedError()

        # Include all sections from template
        sections = []
        for section in template.sections:
            sections.append({
                "section_id": section.id,
                "allow_notes": section.allow_notes,
                "question_count": len(section.questions),
            })

        if not sections:
            raise ValidationError("Template must have at least one section")

        # Generate unique share_id
        share_id = await self._ensure_unique_share_id()

        # Create survey
        survey_data = {
            "template_id": template.id,
            "attraction_id": ObjectId(attraction_id),
            "name": name,
            "status": SurveyStatus.DRAFT.value,
            "sections": sections,
            "share_id": share_id,
        }

        survey = await self.survey_repo.create(survey_data)

        # Invalidate cache after creating survey
        await invalidate_cache("surveys")

        return survey

    async def update_survey(
        self,
        survey_id: str,
        attraction_id: str,
        updates: dict[str, Any],
    ) -> Survey:
        """Update survey (draft only, own attraction only)."""
        survey = await self.get_survey(survey_id, attraction_id)

        if survey.status != SurveyStatus.DRAFT:
            raise BusinessRuleError(
                "BR-SRV-002",
                "Can only modify draft surveys"
            )

        # Filter allowed updates
        allowed = {"name"}
        filtered = {k: v for k, v in updates.items() if k in allowed}

        if not filtered:
            return survey

        updated = await self.survey_repo.update(survey_id, filtered)
        if not updated:
            raise NotFoundError("Survey", survey_id)

        # Invalidate cache after updating survey
        await invalidate_cache("surveys")

        return updated

    async def delete_survey(
        self,
        survey_id: str,
        attraction_id: str,
    ) -> None:
        """Delete survey (draft only, own attraction only)."""
        survey = await self.get_survey(survey_id, attraction_id)

        if survey.status != SurveyStatus.DRAFT:
            raise BusinessRuleError(
                "BR-SRV-003",
                "Can only delete draft surveys"
            )

        # Check for responses
        if await self.survey_repo.has_responses(survey_id):
            raise BusinessRuleError(
                "BR-SRV-004",
                "Cannot delete survey with submitted responses"
            )

        await self.survey_repo.delete(survey_id)

        # Invalidate cache after deleting survey
        await invalidate_cache("surveys")

    async def publish_survey(
        self,
        survey_id: str,
        attraction_id: str,
    ) -> Survey:
        """
        Publish survey.

        Business rules:
        - BR-SRV-001: Archive currently published survey for attraction first
        - Can only publish own surveys
        """
        survey = await self.get_survey(survey_id, attraction_id)

        if survey.status == SurveyStatus.PUBLISHED:
            raise ValidationError("Survey is already published")

        if survey.status == SurveyStatus.ARCHIVED:
            raise ValidationError("Cannot publish archived survey")

        # Archive currently published survey (BR-SRV-001)
        await self.survey_repo.archive_published_for_attraction(attraction_id)

        # Publish this survey
        published = await self.survey_repo.publish(survey_id)
        if not published:
            raise NotFoundError("Survey", survey_id)

        # Invalidate cache after publishing survey
        await invalidate_cache("surveys")

        return published

    async def archive_survey(
        self,
        survey_id: str,
        attraction_id: str,
    ) -> Survey:
        """Archive survey."""
        survey = await self.get_survey(survey_id, attraction_id)

        if survey.status == SurveyStatus.ARCHIVED:
            raise ValidationError("Survey is already archived")

        archived = await self.survey_repo.archive(survey_id)
        if not archived:
            raise NotFoundError("Survey", survey_id)

        # Invalidate cache after archiving survey
        await invalidate_cache("surveys")

        return archived

    def get_public_url(self, share_id: str) -> str:
        """Get public URL for survey."""
        return f"{settings.base_url}/survey/{share_id}"

    async def get_qr_code(
        self,
        survey_id: str,
        attraction_id: str,
    ) -> bytes:
        """
        Generate QR code for survey.

        Returns PNG image bytes.
        """
        survey = await self.get_survey(survey_id, attraction_id)

        # Generate QR code
        qr_bytes = generate_survey_qr(settings.base_url, survey.share_id)

        return qr_bytes

    async def update_qr_code_url(
        self,
        survey_id: str,
        qr_code_url: str,
    ) -> Survey:
        """Update survey QR code URL."""
        updated = await self.survey_repo.update_qr_code(survey_id, qr_code_url)
        if not updated:
            raise NotFoundError("Survey", survey_id)
        return updated
