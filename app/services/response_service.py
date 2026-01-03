"""Survey response service for business logic."""
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId

from app.core.exceptions import (
    NotFoundError,
    ForbiddenError,
    SurveyNotPublishedError,
    DuplicateResponseError,
)
from app.models.domain import (
    SurveyResponse,
    QuestionType,
    QuestionTag,
)
from app.models.schemas.survey import (
    PublicSurveyResponse,
    PublicSurveySection,
    PublicSurveyQuestion,
)
from app.models.schemas.response import (
    ResponseSubmit,
    ResponseSubmitResult,
    SurveyAnalytics,
    TagScoreAnalytics,
    DailyTrendItem,
)
from app.repositories.response_repository import ResponseRepository
from app.repositories.survey_repository import SurveyRepository
from app.repositories.template_repository import TemplateRepository


class ResponseService:
    """Service for survey response operations."""

    def __init__(
        self,
        response_repo: ResponseRepository,
        survey_repo: SurveyRepository,
        template_repo: TemplateRepository,
    ):
        self.response_repo = response_repo
        self.survey_repo = survey_repo
        self.template_repo = template_repo

    async def get_public_survey(self, share_id: str) -> PublicSurveyResponse:
        """
        Get survey data for public display.

        Returns survey structure with selected sections and questions.
        """
        survey = await self.survey_repo.find_published_by_share_id(share_id)
        if not survey:
            raise SurveyNotPublishedError()

        template = await self.template_repo.find_by_id(survey.template_id)
        if not template:
            raise NotFoundError("Template", str(survey.template_id))

        # Get attraction name
        attraction_name = survey.name  # Fallback, could fetch attraction

        # Build public survey response with only selected sections
        selected_section_ids = {str(s.section_id) for s in survey.sections}
        section_settings = {str(s.section_id): s for s in survey.sections}

        public_sections = []
        for section in template.sections:
            if str(section.id) not in selected_section_ids:
                continue

            settings = section_settings.get(str(section.id))
            public_questions = []

            for question in section.questions:
                q_config = None
                if question.config:
                    q_config = question.config.model_dump()

                public_questions.append(
                    PublicSurveyQuestion(
                        id=str(question.id),
                        text=question.text,
                        type=question.type.value,
                        tag=question.tag.value,
                        allow_na=question.allow_na,
                        config=q_config,
                    )
                )

            public_sections.append(
                PublicSurveySection(
                    id=str(section.id),
                    title=section.title,
                    allow_notes=settings.allow_notes if settings else False,
                    questions=public_questions,
                )
            )

        return PublicSurveyResponse(
            share_id=share_id,
            name=survey.name,
            attraction_name=attraction_name,
            sections=public_sections,
        )

    async def submit_response(
        self,
        share_id: str,
        data: ResponseSubmit,
        fingerprint: str | None = None,
        client_ip: str | None = None,
    ) -> ResponseSubmitResult:
        """
        Submit survey response.

        Args:
            share_id: Survey share ID
            data: Response submission data
            fingerprint: Optional duplicate detection fingerprint
            client_ip: Client IP for fallback fingerprint

        Returns:
            Submission result with response ID
        """
        # Get published survey
        survey = await self.survey_repo.find_published_by_share_id(share_id)
        if not survey:
            raise SurveyNotPublishedError()

        # Generate fingerprint if not provided
        effective_fingerprint = fingerprint or client_ip

        # Check for duplicate (BR-RSP-003: 12-hour window)
        if effective_fingerprint:
            if await self.response_repo.check_duplicate(
                str(survey.id), effective_fingerprint
            ):
                raise DuplicateResponseError()

        # Get template for scoring
        template = await self.template_repo.find_by_id(survey.template_id)
        if not template:
            raise NotFoundError("Template", str(survey.template_id))

        # Build question lookup
        question_lookup = {}
        section_lookup = {}
        for section in template.sections:
            section_lookup[str(section.id)] = section
            for question in section.questions:
                question_lookup[str(question.id)] = question

        # Process sections and calculate scores
        processed_sections = []
        tag_scores: dict[str, list[float]] = {}
        section_scores: dict[str, float] = {}

        for section_data in data.sections:
            section_id = section_data.section_id
            section = section_lookup.get(section_id)
            if not section:
                continue

            questions_responses = []
            section_question_scores = []

            for answer in section_data.questions:
                question_id = answer.question_id
                question = question_lookup.get(question_id)
                if not question:
                    continue

                value = answer.value
                score = self._calculate_question_score(value, question)

                questions_responses.append({
                    "question_id": ObjectId(question_id),
                    "type": question.type.value,
                    "value": value,
                    "score": score,
                    "tag": question.tag.value,
                })

                if score is not None:
                    section_question_scores.append(score)
                    tag_key = question.tag.value
                    if tag_key not in tag_scores:
                        tag_scores[tag_key] = []
                    tag_scores[tag_key].append(score)

            # Calculate section average
            if section_question_scores:
                section_scores[section_id] = (
                    sum(section_question_scores) / len(section_question_scores)
                )

            processed_sections.append({
                "section_id": ObjectId(section_id),
                "note": section_data.note,
                "questions": questions_responses,
            })

        # Calculate tag averages
        tag_averages = {
            tag: sum(scores) / len(scores)
            for tag, scores in tag_scores.items()
            if scores
        }

        # Create response document
        response_data = {
            "survey_id": survey.id,
            "attraction_id": survey.attraction_id,
            "template_id": survey.template_id,
            "submitted_at": datetime.utcnow(),
            "sections": processed_sections,
            "tag_scores": tag_averages,
            "section_scores": section_scores,
            "weather_snapshot": None,
            "duplicate_fingerprint": effective_fingerprint,
        }

        response = await self.response_repo.create(response_data)

        return ResponseSubmitResult(
            id=str(response.id),
            message="Thank you for your feedback!",
            tag_scores=tag_averages if tag_averages else None,
        )

    def _calculate_question_score(
        self,
        value: Any,
        question: Any,
    ) -> float | None:
        """Calculate score for a single question answer."""
        if value is None:
            return None  # N/A response

        if question.type == QuestionType.YES_NO:
            if question.config:
                config = question.config
                if value is True or value == "yes":
                    return config.yes_weight
                return config.no_weight
            return 1.0 if value in (True, "yes") else 0.0

        elif question.type == QuestionType.NUMERIC:
            if question.config:
                config = question.config
                range_size = config.max_value - config.min_value
                if range_size > 0:
                    normalized = (value - config.min_value) / range_size
                    return max(0.0, min(1.0, normalized))
            return float(value) / 10.0  # Default 0-10 scale

        elif question.type == QuestionType.DROPDOWN:
            if question.config and hasattr(question.config, 'options'):
                for option in question.config.options:
                    if option.value == value:
                        return option.weight
            return 0.0

        return None

    async def list_responses(
        self,
        attraction_id: str | None,
        survey_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SurveyResponse], int]:
        """List responses with filtering. If attraction_id is None, returns all responses (Super Admin)."""
        if survey_id:
            responses = await self.response_repo.find_by_survey(
                survey_id, skip=skip, limit=limit
            )
            total = await self.response_repo.count_by_survey(survey_id)
        elif attraction_id:
            responses = await self.response_repo.find_by_attraction(
                attraction_id, skip=skip, limit=limit
            )
            total = await self.response_repo.count_by_attraction(attraction_id)
        else:
            # Super Admin: get all responses
            responses = await self.response_repo.find_many(
                {}, skip=skip, limit=limit, sort=[("submitted_at", -1)]
            )
            total = await self.response_repo.count({})

        return responses, total

    async def get_response(
        self,
        response_id: str,
        attraction_id: str | None,
    ) -> SurveyResponse:
        """Get response by ID. If attraction_id is None (Super Admin), no ownership check."""
        response = await self.response_repo.find_by_id(response_id)
        if not response:
            raise NotFoundError("Response", response_id)

        # Check attraction ownership (skip for Super Admin)
        if attraction_id is not None and str(response.attraction_id) != attraction_id:
            raise ForbiddenError("Access denied to this response")

        return response

    async def get_survey_analytics(
        self,
        survey_id: str,
        attraction_id: str | None,
    ) -> SurveyAnalytics:
        """Get analytics for a specific survey. If attraction_id is None (Super Admin), no ownership check."""
        # Verify survey belongs to attraction (skip for Super Admin)
        if attraction_id is not None:
            survey = await self.survey_repo.find_by_id(survey_id)
            if not survey:
                raise NotFoundError("Survey", survey_id)
            if str(survey.attraction_id) != attraction_id:
                raise ForbiddenError("Access denied to this survey")

        analytics = await self.response_repo.get_survey_analytics(survey_id)

        tag_averages = []
        for tag, data in analytics.get("tag_scores", {}).items():
            tag_averages.append(
                TagScoreAnalytics(
                    tag=tag,
                    average=data.get("average", 0),
                    count=data.get("count", 0),
                )
            )

        return SurveyAnalytics(
            survey_id=survey_id,
            total_responses=analytics.get("total", 0),
            tag_averages=tag_averages,
            section_averages=analytics.get("section_scores", {}),
        )

    async def get_attraction_analytics(
        self,
        attraction_id: str | None,
    ) -> SurveyAnalytics:
        """Get aggregate analytics for attraction surveys. If attraction_id is None (Super Admin), returns global analytics."""
        analytics = await self.response_repo.get_attraction_analytics(attraction_id)

        tag_averages = []
        for tag, data in analytics.get("tag_scores", {}).items():
            tag_averages.append(
                TagScoreAnalytics(
                    tag=tag,
                    average=data.get("average", 0),
                    count=data.get("count", 0),
                )
            )

        return SurveyAnalytics(
            survey_id="all",
            total_responses=analytics.get("total", 0),
            tag_averages=tag_averages,
            section_averages=analytics.get("section_scores", {}),
        )

    async def get_daily_trend(
        self,
        attraction_id: str | None,
        survey_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        days: int = 30,
    ) -> list[DailyTrendItem]:
        """Get daily response trends. If attraction_id is None (Super Admin), returns global trends."""
        # Set date range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=days)

        trends = await self.response_repo.get_daily_trend(
            attraction_id=attraction_id,
            survey_id=survey_id,
            start_date=start_date,
            end_date=end_date,
        )

        return [
            DailyTrendItem(
                date=t["date"],
                count=t["count"],
                tag_averages=t.get("tag_averages", {}),
            )
            for t in trends
        ]
