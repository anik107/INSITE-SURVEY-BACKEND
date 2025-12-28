"""Survey request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.domain import SurveyStatus, SurveySection


class SurveySectionResponse(BaseModel):
    """Survey section in response."""
    section_id: str
    allow_notes: bool
    question_count: int


class SurveyCreate(BaseModel):
    """Request to create survey from published template."""
    name: str = Field(..., min_length=1, max_length=200)


class SurveyUpdate(BaseModel):
    """Request to update survey (draft only)."""
    name: str | None = Field(None, min_length=1, max_length=200)


class SurveyResponse(BaseModel):
    """Full survey response."""
    id: str
    template_id: str
    attraction_id: str
    name: str
    status: SurveyStatus
    sections: list[SurveySectionResponse]
    share_id: str
    qr_code_url: str | None
    published_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, survey) -> "SurveyResponse":
        """Create from domain model."""
        sections = [
            SurveySectionResponse(
                section_id=str(s.section_id),
                allow_notes=s.allow_notes,
                question_count=s.question_count,
            )
            for s in survey.sections
        ]
        return cls(
            id=str(survey.id),
            template_id=str(survey.template_id),
            attraction_id=str(survey.attraction_id),
            name=survey.name,
            status=survey.status,
            sections=sections,
            share_id=survey.share_id,
            qr_code_url=survey.qr_code_url,
            published_at=survey.published_at,
            archived_at=survey.archived_at,
            created_at=survey.created_at,
            updated_at=survey.updated_at,
        )


class SurveyListItem(BaseModel):
    """Survey in list response."""
    id: str
    name: str
    status: SurveyStatus
    share_id: str
    qr_code_url: str | None
    published_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, survey) -> "SurveyListItem":
        """Create from domain model."""
        return cls(
            id=str(survey.id),
            name=survey.name,
            status=survey.status,
            share_id=survey.share_id,
            qr_code_url=survey.qr_code_url,
            published_at=survey.published_at,
            created_at=survey.created_at,
        )


class PublicSurveyQuestion(BaseModel):
    """Question in public survey view."""
    id: str
    text: str
    type: str
    tag: str
    allow_na: bool
    config: dict | None = None


class PublicSurveySection(BaseModel):
    """Section in public survey view."""
    id: str
    title: str
    allow_notes: bool
    questions: list[PublicSurveyQuestion]


class PublicSurveyResponse(BaseModel):
    """Public survey for visitors to fill."""
    share_id: str
    name: str
    attraction_name: str
    sections: list[PublicSurveySection]
