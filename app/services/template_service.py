"""Template service for business logic."""
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    BusinessRuleError,
    ConflictError,
)
from app.models.domain import Template, TemplateStatus, Section, Question
from app.repositories.template_repository import TemplateRepository


class TemplateService:
    """Service for template management operations."""

    def __init__(self, template_repo: TemplateRepository):
        self.template_repo = template_repo

    async def _ensure_template_mutable(
        self,
        template: Template,
        action: str,
    ) -> Template:
        """Ensure template can be modified by downgrading published ones to draft."""
        if template.status == TemplateStatus.ARCHIVED:
            raise BusinessRuleError(
                "BR-TPL-004",
                f"Cannot {action} an archived template",
            )

        if template.status == TemplateStatus.PUBLISHED:
            demoted = await self.template_repo.update(
                template.id,
                {"status": TemplateStatus.DRAFT.value},
            )
            return demoted or template

        return template

    async def list_templates(
        self,
        status: TemplateStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Template], int]:
        """List templates with optional filtering."""
        if status:
            templates = await self.template_repo.find_by_status(status, skip, limit)
            total = await self.template_repo.count_by_status(status)
        else:
            templates = await self.template_repo.find_many(
                skip=skip,
                limit=limit,
                sort=[("updated_at", -1)],
            )
            total = await self.template_repo.count()

        return templates, total

    async def get_template(self, template_id: str) -> Template:
        """Get template by ID."""
        template = await self.template_repo.find_by_id(template_id)
        if not template:
            raise NotFoundError("Template", template_id)
        return template

    async def get_published_template(self) -> Template | None:
        """Get currently published template."""
        return await self.template_repo.find_published()

    async def create_template(
        self,
        title: str,
        created_by: str,
        sections: list[dict] | None = None,
    ) -> Template:
        """Create new template in draft status."""
        template_data = {
            "title": title,
            "status": TemplateStatus.DRAFT.value,
            "sections": sections or [],
            "created_by": ObjectId(created_by),
        }
        return await self.template_repo.create(template_data)

    async def update_template(
        self,
        template_id: str,
        updates: dict[str, Any],
    ) -> Template:
        """Update template metadata and status."""
        template = await self.get_template(template_id)

        # Filter allowed updates
        allowed = {"title", "status", "sections"}
        filtered = {k: v for k, v in updates.items() if k in allowed}

        if (
            template.status == TemplateStatus.ARCHIVED
            and (
                "status" not in filtered
                or filtered.get("status") == TemplateStatus.ARCHIVED.value
            )
        ):
            raise BusinessRuleError(
                "BR-TPL-004",
                "Cannot update archived template",
            )

        # Convert sections to dict format if present
        if "sections" in filtered and filtered["sections"]:
            sections_data = []
            for section in filtered["sections"]:
                questions_data = []
                for q in section['questions']:
                    q_id = None
                    if q.get('id'):
                        try:
                            q_id = ObjectId(q['id'])
                        except:
                            q_id = None
                    q_dict = {
                        "_id": q_id or ObjectId(),
                        "text": q['text'],
                        "type": q['type'],
                        "tag": q['tag'],
                        "allow_na": q['allow_na'],
                    }
                    if q.get('config'):
                        q_dict["config"] = q['config']
                    questions_data.append(q_dict)

                s_id = None
                if section.get('id'):
                    try:
                        s_id = ObjectId(section['id'])
                    except:
                        s_id = None
                sections_data.append({
                    "_id": s_id or ObjectId(),
                    "title": section['title'],
                    "weight": section['weight'],
                    "allow_notes": section['allow_notes'],
                    "questions": questions_data,
                })
            filtered["sections"] = sections_data

        # If publishing, unpublish current published template (set to draft)
        if "status" in filtered and filtered["status"] == TemplateStatus.PUBLISHED.value:
            await self.template_repo.unpublish_published()

        if not filtered:
            return template

        updated = await self.template_repo.update(template_id, filtered)
        if not updated:
            raise NotFoundError("Template", template_id)
        return updated

    async def delete_template(self, template_id: str) -> None:
        """Delete template (draft only, no responses)."""
        template = await self.get_template(template_id)

        if template.status != TemplateStatus.DRAFT:
            raise BusinessRuleError(
                "BR-TPL-003",
                "Only draft templates can be deleted"
            )

        # Check for associated surveys
        if await self.template_repo.has_responses(template_id):
            raise ConflictError("Cannot delete template with associated surveys")

        await self.template_repo.delete(template_id)

    async def publish_template(self, template_id: str) -> Template:
        """
        Publish template.

        Business rules:
        - BR-TPL-001: Unpublish (set to draft) currently published template first
        - Only one template can be published at a time
        - Template must have at least one section
        - Each section must have at least one question
        """
        template = await self.get_template(template_id)

        if template.status == TemplateStatus.PUBLISHED:
            raise ValidationError("Template is already published")

        if template.status == TemplateStatus.ARCHIVED:
            raise ValidationError("Cannot publish archived template")

        # Validate template has sections
        if not template.sections:
            raise ValidationError("Template must have at least one section")

        # Validate each section has questions
        for section in template.sections:
            if not section.questions:
                raise ValidationError(
                    f"Section '{section.title}' must have at least one question"
                )

        # Unpublish currently published template (set to draft) (BR-TPL-001)
        await self.template_repo.unpublish_published()

        # Publish this template
        published = await self.template_repo.publish(template_id)
        if not published:
            raise NotFoundError("Template", template_id)
        return published

    async def archive_template(self, template_id: str) -> Template:
        """Archive template."""
        template = await self.get_template(template_id)

        if template.status == TemplateStatus.ARCHIVED:
            raise ValidationError("Template is already archived")

        archived = await self.template_repo.update(
            template_id,
            {"status": TemplateStatus.ARCHIVED.value}
        )
        if not archived:
            raise NotFoundError("Template", template_id)
        return archived

    async def duplicate_template(
        self,
        template_id: str,
        new_title: str,
        created_by: str,
    ) -> Template:
        """Create a copy of template as draft."""
        template = await self.get_template(template_id)

        # Deep copy sections and questions
        sections_copy = []
        for section in template.sections:
            section_dict = section.model_dump(by_alias=True)
            section_dict["_id"] = ObjectId()
            for question in section_dict.get("questions", []):
                question["_id"] = ObjectId()
            sections_copy.append(section_dict)

        return await self.create_template(
            title=new_title,
            created_by=created_by,
            sections=sections_copy,
        )

    # Section operations
    async def add_section(
        self,
        template_id: str,
        section_data: dict,
    ) -> Template:
        """Add section to template (draft only)."""
        template = await self.get_template(template_id)
        template = await self._ensure_template_mutable(template, "add sections to")

        updated = await self.template_repo.add_section(template_id, section_data)
        if not updated:
            raise NotFoundError("Template", template_id)
        return updated

    async def update_section(
        self,
        template_id: str,
        section_id: str,
        updates: dict,
    ) -> Template:
        """Update section in template."""
        template = await self.get_template(template_id)
        template = await self._ensure_template_mutable(template, "update sections of")

        # Find section
        section_exists = any(str(s.id) == section_id for s in template.sections)
        if not section_exists:
            raise NotFoundError("Section", section_id)

        updated = await self.template_repo.update_section(
            template_id, section_id, updates
        )
        if not updated:
            raise NotFoundError("Template", template_id)
        return updated

    async def remove_section(
        self,
        template_id: str,
        section_id: str,
    ) -> Template:
        """Remove section from template."""
        template = await self.get_template(template_id)
        await self._ensure_template_mutable(template, "remove sections from")

        updated = await self.template_repo.remove_section(template_id, section_id)
        if not updated:
            raise NotFoundError("Template", template_id)
        return updated

    async def reorder_sections(
        self,
        template_id: str,
        section_ids: list[str],
    ) -> Template:
        """Reorder sections in template."""
        template = await self.get_template(template_id)
        await self._ensure_template_mutable(template, "reorder sections for")

        updated = await self.template_repo.reorder_sections(template_id, section_ids)
        if not updated:
            raise NotFoundError("Template", template_id)
        return updated

    # Question operations
    async def add_question(
        self,
        template_id: str,
        section_id: str,
        question_data: dict,
    ) -> Template:
        """Add question to section."""
        template = await self.get_template(template_id)
        await self._ensure_template_mutable(template, "add questions to")

        updated = await self.template_repo.add_question(
            template_id, section_id, question_data
        )
        if not updated:
            raise NotFoundError("Section", section_id)
        return updated

    async def update_question(
        self,
        template_id: str,
        section_id: str,
        question_id: str,
        updates: dict,
    ) -> Template:
        """Update question in section."""
        template = await self.get_template(template_id)
        await self._ensure_template_mutable(template, "update questions in")

        updated = await self.template_repo.update_question(
            template_id, section_id, question_id, updates
        )
        if not updated:
            raise NotFoundError("Question", question_id)
        return updated

    async def remove_question(
        self,
        template_id: str,
        section_id: str,
        question_id: str,
    ) -> Template:
        """Remove question from section."""
        template = await self.get_template(template_id)
        await self._ensure_template_mutable(template, "remove questions from")

        updated = await self.template_repo.remove_question(
            template_id, section_id, question_id
        )
        if not updated:
            raise NotFoundError("Question", question_id)
        return updated
