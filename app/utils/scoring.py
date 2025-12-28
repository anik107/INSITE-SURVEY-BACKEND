"""Survey response scoring utilities."""
from typing import Any

from app.models.domain import (
    QuestionType,
    QuestionTag,
    Question,
    Section,
    YesNoConfig,
    NumericConfig,
    DropdownConfig,
)


def calculate_question_score(
    question: Question,
    value: Any,
) -> float | None:
    """
    Calculate normalized score (0-1) for a question response.

    Args:
        question: Question definition with type and config
        value: Response value

    Returns:
        Normalized score between 0 and 1, or None if N/A
    """
    if value is None:
        return None

    if question.type == QuestionType.YES_NO:
        config = question.config
        if isinstance(config, YesNoConfig):
            if value is True or value == "yes":
                return config.yes_weight
            elif value is False or value == "no":
                return config.no_weight
        # Default yes/no scoring
        return 1.0 if value in (True, "yes") else 0.0

    elif question.type == QuestionType.NUMERIC:
        config = question.config
        if isinstance(config, NumericConfig):
            min_val = config.min_value
            max_val = config.max_value
            if max_val == min_val:
                return 1.0 if value == max_val else 0.0
            # Normalize to 0-1 range
            normalized = (value - min_val) / (max_val - min_val)
            return max(0.0, min(1.0, normalized))
        # Default: assume 0-5 scale
        return max(0.0, min(1.0, value / 5.0))

    elif question.type == QuestionType.DROPDOWN:
        config = question.config
        if isinstance(config, DropdownConfig):
            for option in config.options:
                if option.value == value:
                    return option.weight
        return 0.0

    return None


def calculate_section_score(
    section: Section,
    question_scores: dict[str, float | None],
) -> float | None:
    """
    Calculate weighted section score.

    Args:
        section: Section definition with questions
        question_scores: Map of question_id -> score

    Returns:
        Section score (0-1) or None if all questions are N/A
    """
    valid_scores = []
    for question in section.questions:
        q_id = str(question.id)
        score = question_scores.get(q_id)
        if score is not None:
            valid_scores.append(score)

    if not valid_scores:
        return None

    return sum(valid_scores) / len(valid_scores)


def calculate_tag_scores(
    sections: list[Section],
    question_scores: dict[str, float | None],
) -> dict[QuestionTag, float]:
    """
    Calculate aggregate scores by question tag.

    Args:
        sections: List of sections with questions
        question_scores: Map of question_id -> score

    Returns:
        Map of tag -> average score
    """
    tag_scores: dict[QuestionTag, list[float]] = {
        QuestionTag.SPACES_PLACES: [],
        QuestionTag.EMPATHY_EMOTION: [],
        QuestionTag.STORYTELLING: [],
    }

    for section in sections:
        for question in section.questions:
            q_id = str(question.id)
            score = question_scores.get(q_id)
            if score is not None:
                tag_scores[question.tag].append(score)

    result = {}
    for tag, scores in tag_scores.items():
        if scores:
            result[tag] = sum(scores) / len(scores)

    return result


def calculate_overall_score(
    sections: list[Section],
    section_scores: dict[str, float | None],
) -> float | None:
    """
    Calculate weighted overall score based on section weights.

    Args:
        sections: List of sections with weights
        section_scores: Map of section_id -> score

    Returns:
        Overall weighted score (0-1) or None if no valid sections
    """
    total_weight = 0
    weighted_sum = 0.0

    for section in sections:
        s_id = str(section.id)
        score = section_scores.get(s_id)
        if score is not None:
            weighted_sum += score * section.weight
            total_weight += section.weight

    if total_weight == 0:
        return None

    return weighted_sum / total_weight
