"""Template repository for database operations."""
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import Template, TemplateStatus, Section, Question
from app.repositories.base import BaseRepository


class TemplateRepository(BaseRepository[Template]):
    """Repository for Template collection operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "templates", Template)

    async def find_published(self) -> Template | None:
        """Find the currently published template."""
        return await self.find_one({"status": TemplateStatus.PUBLISHED.value})

    async def find_by_status(
        self,
        status: TemplateStatus,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Template]:
        """Find templates by status."""
        return await self.find_many(
            {"status": status.value},
            skip=skip,
            limit=limit,
            sort=[("updated_at", -1)],
        )

    async def count_by_status(self, status: TemplateStatus | None = None) -> int:
        """Count templates by status."""
        filter = {}
        if status:
            filter["status"] = status.value
        return await self.count(filter)

    async def archive_published(self) -> bool:
        """Archive currently published template."""
        result = await self.collection.update_one(
            {"status": TemplateStatus.PUBLISHED.value},
            {
                "$set": {
                    "status": TemplateStatus.ARCHIVED.value,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0

    async def publish(self, template_id: str | ObjectId) -> Template | None:
        """Publish a template."""
        now = datetime.utcnow()
        return await self.update(
            template_id,
            {
                "status": TemplateStatus.PUBLISHED.value,
                "published_at": now,
            },
        )

    async def add_section(
        self,
        template_id: str | ObjectId,
        section_data: dict,
    ) -> Template | None:
        """Add section to template."""
        section_data["_id"] = ObjectId()
        result = await self.collection.find_one_and_update(
            {"_id": self._to_object_id(template_id)},
            {
                "$push": {"sections": section_data},
                "$set": {"updated_at": datetime.utcnow()},
            },
            return_document=True,
        )
        return self._doc_to_model(result)

    async def update_section(
        self,
        template_id: str | ObjectId,
        section_id: str | ObjectId,
        updates: dict,
    ) -> Template | None:
        """Update specific section in template."""
        set_updates = {f"sections.$.{k}": v for k, v in updates.items()}
        set_updates["updated_at"] = datetime.utcnow()

        result = await self.collection.find_one_and_update(
            {
                "_id": self._to_object_id(template_id),
                "sections._id": self._to_object_id(section_id),
            },
            {"$set": set_updates},
            return_document=True,
        )
        return self._doc_to_model(result)

    async def remove_section(
        self,
        template_id: str | ObjectId,
        section_id: str | ObjectId,
    ) -> Template | None:
        """Remove section from template."""
        result = await self.collection.find_one_and_update(
            {"_id": self._to_object_id(template_id)},
            {
                "$pull": {"sections": {"_id": self._to_object_id(section_id)}},
                "$set": {"updated_at": datetime.utcnow()},
            },
            return_document=True,
        )
        return self._doc_to_model(result)

    async def reorder_sections(
        self,
        template_id: str | ObjectId,
        section_ids: list[str],
    ) -> Template | None:
        """Reorder sections in template."""
        template = await self.find_by_id(template_id)
        if not template:
            return None

        # Create a map of section_id to section
        section_map = {str(s.id): s for s in template.sections}

        # Reorder based on provided IDs
        reordered = []
        for sid in section_ids:
            if sid in section_map:
                reordered.append(section_map[sid].model_dump(by_alias=True))

        result = await self.collection.find_one_and_update(
            {"_id": self._to_object_id(template_id)},
            {
                "$set": {
                    "sections": reordered,
                    "updated_at": datetime.utcnow(),
                }
            },
            return_document=True,
        )
        return self._doc_to_model(result)

    async def add_question(
        self,
        template_id: str | ObjectId,
        section_id: str | ObjectId,
        question_data: dict,
    ) -> Template | None:
        """Add question to section."""
        question_data["_id"] = ObjectId()
        result = await self.collection.find_one_and_update(
            {
                "_id": self._to_object_id(template_id),
                "sections._id": self._to_object_id(section_id),
            },
            {
                "$push": {"sections.$.questions": question_data},
                "$set": {"updated_at": datetime.utcnow()},
            },
            return_document=True,
        )
        return self._doc_to_model(result)

    async def update_question(
        self,
        template_id: str | ObjectId,
        section_id: str | ObjectId,
        question_id: str | ObjectId,
        updates: dict,
    ) -> Template | None:
        """Update specific question in section."""
        # First get the template to find array indices
        template = await self.find_by_id(template_id)
        if not template:
            return None

        # Find section index
        section_idx = None
        question_idx = None
        for si, section in enumerate(template.sections):
            if str(section.id) == str(section_id):
                section_idx = si
                for qi, question in enumerate(section.questions):
                    if str(question.id) == str(question_id):
                        question_idx = qi
                        break
                break

        if section_idx is None or question_idx is None:
            return None

        # Build update path
        set_updates = {
            f"sections.{section_idx}.questions.{question_idx}.{k}": v
            for k, v in updates.items()
        }
        set_updates["updated_at"] = datetime.utcnow()

        result = await self.collection.find_one_and_update(
            {"_id": self._to_object_id(template_id)},
            {"$set": set_updates},
            return_document=True,
        )
        return self._doc_to_model(result)

    async def remove_question(
        self,
        template_id: str | ObjectId,
        section_id: str | ObjectId,
        question_id: str | ObjectId,
    ) -> Template | None:
        """Remove question from section."""
        result = await self.collection.find_one_and_update(
            {
                "_id": self._to_object_id(template_id),
                "sections._id": self._to_object_id(section_id),
            },
            {
                "$pull": {"sections.$.questions": {"_id": self._to_object_id(question_id)}},
                "$set": {"updated_at": datetime.utcnow()},
            },
            return_document=True,
        )
        return self._doc_to_model(result)

    async def has_responses(self, template_id: str | ObjectId) -> bool:
        """Check if template has any survey responses."""
        # This requires checking surveys using this template
        # For now, we'll check if any surveys reference this template
        db = self.collection.database
        count = await db.surveys.count_documents(
            {"template_id": self._to_object_id(template_id)},
            limit=1,
        )
        return count > 0
