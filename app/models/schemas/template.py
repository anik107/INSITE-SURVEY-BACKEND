"""Template schemas for request/response."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.domain import (
    TemplateStatus,
    QuestionType,
    QuestionTag,
    YesNoConfig,
    NumericConfig,
    DropdownConfig,
    DropdownOption,
)


# Question schemas
class QuestionCreate(BaseModel):
    """Create question request."""
    id: str | None = None
    text: str = Field(min_length=1, max_length=1000)
    type: QuestionType
    tag: QuestionTag
    allow_na: bool = False
    config: YesNoConfig | NumericConfig | DropdownConfig | None = None


class QuestionUpdate(BaseModel):
    """Update question request."""
    text: str | None = Field(default=None, min_length=1, max_length=1000)
    type: QuestionType | None = None
    tag: QuestionTag | None = None
    allow_na: bool | None = None
    config: YesNoConfig | NumericConfig | DropdownConfig | None = None


class QuestionResponse(BaseModel):
    """Question response."""
    id: str
    text: str
    type: QuestionType
    tag: QuestionTag
    allow_na: bool
    config: dict | None = None


# Section schemas
class SectionCreate(BaseModel):
    """Create section request."""
    id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    weight: int = Field(default=5, ge=1, le=100)
    allow_notes: bool = False
    questions: list[QuestionCreate] = Field(default_factory=list)


class SectionUpdate(BaseModel):
    """Update section request."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    weight: int | None = Field(default=None, ge=1, le=10)
    allow_notes: bool | None = None


class SectionResponse(BaseModel):
    """Section response."""
    id: str
    title: str
    weight: int
    allow_notes: bool
    questions: list[QuestionResponse]


class SectionReorderRequest(BaseModel):
    """Reorder sections request."""
    section_ids: list[str] = Field(min_length=1)


# Template schemas
class TemplateCreate(BaseModel):
    """Create template request."""
    title: str = Field(min_length=1, max_length=200)
    sections: list[SectionCreate] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    """Update template request."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: TemplateStatus | None = None
    sections: list[SectionCreate] | None = None


class TemplateResponse(BaseModel):
    """Template response."""
    id: str
    title: str
    status: TemplateStatus
    sections: list[SectionResponse]
    published_at: datetime | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, template) -> "TemplateResponse":
        """Convert domain model to response."""
        sections = []
        for section in template.sections:
            questions = []
            for q in section.questions:
                q_config = None
                if q.config:
                    q_config = q.config.model_dump()
                questions.append(QuestionResponse(
                    id=str(q.id),
                    text=q.text,
                    type=q.type,
                    tag=q.tag,
                    allow_na=q.allow_na,
                    config=q_config,
                ))
            sections.append(SectionResponse(
                id=str(section.id),
                title=section.title,
                weight=section.weight,
                allow_notes=section.allow_notes,
                questions=questions,
            ))

        return cls(
            id=str(template.id),
            title=template.title,
            status=template.status,
            sections=sections,
            published_at=template.published_at,
            created_by=str(template.created_by) if template.created_by else None,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


class TemplateListItem(BaseModel):
    """Template list item (without full sections)."""
    id: str
    title: str
    status: TemplateStatus
    section_count: int
    question_count: int
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, template) -> "TemplateListItem":
        """Convert domain model to list item."""
        section_count = len(template.sections)
        question_count = sum(len(s.questions) for s in template.sections)

        return cls(
            id=str(template.id),
            title=template.title,
            status=template.status,
            section_count=section_count,
            question_count=question_count,
            published_at=template.published_at,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
