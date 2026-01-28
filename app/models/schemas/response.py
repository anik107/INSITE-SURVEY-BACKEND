"""Survey response request/response schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.domain import QuestionType, QuestionTag


class QuestionAnswerSubmit(BaseModel):
    """Single question answer in submission."""
    question_id: str
    value: Any = None  # None means N/A


class SectionAnswerSubmit(BaseModel):
    """Section answers in submission."""
    section_id: str
    note: str | None = None
    questions: list[QuestionAnswerSubmit]
    images: list[str] | None = None  # Base64 encoded images


class WeatherSnapshotSubmit(BaseModel):
    """Weather data at time of submission."""
    temperature: float | None = None
    condition: str | None = None
    humidity: float | None = None
    location: str | None = None


class ResponseSubmit(BaseModel):
    """Survey response submission from visitor."""
    sections: list[SectionAnswerSubmit]
    fingerprint: str | None = Field(
        None,
        description="Browser fingerprint for duplicate detection",
    )
    weather_snapshot: WeatherSnapshotSubmit | None = None


class ResponseSubmitResult(BaseModel):
    """Result of response submission."""
    id: str
    message: str = "Thank you for your feedback!"
    tag_scores: dict[str, float] | None = None


class QuestionAnswerResponse(BaseModel):
    """Question answer in response detail."""
    question_id: str
    text: str  # The actual question text
    type: QuestionType
    value: Any
    score: float | None
    tag: QuestionTag


class SectionAnswerResponse(BaseModel):
    """Section answers in response detail."""
    section_id: str
    title: str | None = None
    note: str | None = None
    images: list[str] | None = None  # Base64 encoded images
    questions: list[QuestionAnswerResponse]


class SurveyResponseDetail(BaseModel):
    """Full survey response detail."""
    id: str
    survey_id: str
    attraction_id: str
    template_id: str
    submitted_at: datetime
    sections: list[SectionAnswerResponse]
    tag_scores: dict[str, float]
    section_scores: dict[str, float]
    weather_snapshot: dict[str, Any] | None

    @classmethod
    def from_model(cls, response, template=None) -> "SurveyResponseDetail":
        """Create from domain model.
        
        Args:
            response: The survey response domain model
            template: Optional template to enrich with question text
        """
        # Build question and section lookup if template provided
        question_lookup = {}
        section_lookup = {}
        if template:
            for section in template.sections:
                section_lookup[str(section.id)] = section.title
                for question in section.questions:
                    question_lookup[str(question.id)] = question.text

        sections = []
        for s in response.sections:
            questions = [
                QuestionAnswerResponse(
                    question_id=str(q.question_id),
                    text=question_lookup.get(str(q.question_id), ""),  # Get question text from template
                    type=q.type,
                    value=q.value,
                    score=q.score,
                    tag=q.tag,
                )
                for q in s.questions
            ]
            # Get section title from template
            section_title = section_lookup.get(str(s.section_id), None)
            # Get images from the raw response data (stored as dict)
            section_images = getattr(s, 'images', None) or (s.get('images') if hasattr(s, 'get') else None)
            sections.append(
                SectionAnswerResponse(
                    section_id=str(s.section_id),
                    title=section_title,
                    note=s.note,
                    images=section_images,
                    questions=questions,
                )
            )

        # Convert tag scores enum keys to strings
        tag_scores = {k.value: v for k, v in response.tag_scores.items()}

        return cls(
            id=str(response.id),
            survey_id=str(response.survey_id),
            attraction_id=str(response.attraction_id),
            template_id=str(response.template_id),
            submitted_at=response.submitted_at,
            sections=sections,
            tag_scores=tag_scores,
            section_scores=response.section_scores,
            weather_snapshot=response.weather_snapshot,
        )


class SurveyResponseListItem(BaseModel):
    """Survey response in list view."""
    id: str
    survey_id: str
    submitted_at: datetime
    tag_scores: dict[str, float]

    @classmethod
    def from_model(cls, response) -> "SurveyResponseListItem":
        """Create from domain model."""
        tag_scores = {k.value: v for k, v in response.tag_scores.items()}
        return cls(
            id=str(response.id),
            survey_id=str(response.survey_id),
            submitted_at=response.submitted_at,
            tag_scores=tag_scores,
        )


class TagScoreAnalytics(BaseModel):
    """Tag score analytics."""
    tag: str
    average: float
    count: int


class SurveyAnalytics(BaseModel):
    """Survey-level analytics."""
    survey_id: str
    total_responses: int
    tag_averages: list[TagScoreAnalytics]
    section_averages: dict[str, float]


class DailyTrendItem(BaseModel):
    """Daily response trend item."""
    date: str
    count: int
    tag_averages: dict[str, float]
