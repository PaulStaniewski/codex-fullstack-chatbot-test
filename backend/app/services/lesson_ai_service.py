import logging
import re
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, status
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAIError,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.services import chat_service


logger = logging.getLogger(__name__)

STUDY_ACTIONS = {
    "summarize": "Summarize the lesson material in a concise, beginner-friendly way.",
    "explain": "Explain the lesson material simply, using plain language.",
    "example": "Give a practical example based on the lesson material.",
    "key_points": "List the key points the learner should remember.",
    "ask_questions": "Ask the learner a few short study questions about the material.",
    "custom_question": "Answer the learner's custom question.",
}

DisconnectCallable = Callable[[], Awaitable[bool]]


def build_lesson_tutor_prompt(
    lesson: dict,
    step: dict,
    question: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an AI programming tutor inside a learning platform.\n"
                "You help the user understand the current lesson step.\n"
                "Use the provided lesson context as the source of truth.\n"
                "If the user asks about something outside this lesson, answer briefly and connect "
                "it back to the lesson when possible.\n"
                "Do not give unrelated long explanations.\n"
                "Be friendly, clear, concise, and use simple examples."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Lesson title: {lesson['title']}\n"
                f"Course ID: {lesson['course_id']}\n"
                f"Current step title: {step['title']}\n"
                f"Current step type: {step['type']}\n"
                f"Current step content:\n{step['content']}\n\n"
                f"User question: {question}"
            ),
        },
    ]


def get_reading_steps_for_study(
    lesson: dict,
    reading_step_types: set[str],
    step_index: int | None = None,
) -> list[dict]:
    if step_index is not None:
        if step_index < 0 or step_index >= len(lesson["steps"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid step index")
        step = lesson["steps"][step_index]
        if step["type"] not in reading_step_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Study assistant can focus only on reading steps",
            )
        return [step]

    return [step for step in lesson["steps"] if step["type"] in reading_step_types]


def build_lesson_study_prompt(
    lesson: dict,
    reading_steps: list[dict],
    action: str,
    question: str | None = None,
) -> list[dict[str, str]]:
    action_instruction = STUDY_ACTIONS[action]
    lesson_material = "\n\n".join(
        f"{index + 1}. {step['title']} ({step['type']}):\n{step['content']}"
        for index, step in enumerate(reading_steps)
    )
    custom_question = (question or "").strip()

    return [
        {
            "role": "system",
            "content": (
                "You are an AI study assistant inside a programming learning platform.\n"
                "Use the provided lesson material as the source of truth.\n"
                "Keep answers focused on the lesson.\n"
                "If the user asks about something outside the lesson, answer briefly and connect "
                "it back to the lesson when possible.\n"
                "Be clear, practical, and concise."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Lesson title: {lesson['title']}\n"
                f"Course ID: {lesson['course_id']}\n"
                f"Action: {action}\n"
                f"Instruction: {action_instruction}\n\n"
                f"Lesson material:\n{lesson_material}\n\n"
                f"User question: {custom_question if custom_question else 'No custom question provided.'}"
            ),
        },
    ]


def build_practice_feedback_prompt(
    lesson: dict,
    step: dict,
    answer: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an AI programming tutor reviewing a learner's practice answer.\n"
                "Use the provided lesson and practice instruction as the source of truth.\n"
                "Give concise feedback.\n"
                "Mention what is correct.\n"
                "Mention what is missing or unclear.\n"
                "Suggest one improved answer.\n"
                "Be supportive and not harsh.\n"
                "Do not invent requirements outside the lesson.\n"
                "End with this compact structured section exactly:\n"
                "Score: <0-100>\n"
                "Strengths:\n"
                "- ...\n"
                "Improvements:\n"
                "- ..."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Lesson title: {lesson['title']}\n"
                f"Course ID: {lesson['course_id']}\n"
                f"Practice step title: {step['title']}\n"
                f"Practice instruction:\n{step['content']}\n\n"
                f"User answer:\n{answer}"
            ),
        },
    ]


def _parse_bullets(section_text: str) -> list[str] | None:
    items = [
        line.strip().lstrip("-*").strip()
        for line in section_text.splitlines()
        if line.strip().startswith(("-", "*"))
    ]
    clean_items = [item for item in items if item]
    return clean_items or None


def parse_practice_feedback_metadata(feedback: str) -> dict[str, int | list[str] | None]:
    metadata: dict[str, int | list[str] | None] = {
        "score": None,
        "strengths": None,
        "improvements": None,
    }

    score_match = re.search(r"(?im)^\s*Score:\s*(\d{1,3})\s*$", feedback)
    if score_match:
        score = int(score_match.group(1))
        if 0 <= score <= 100:
            metadata["score"] = score

    strengths_match = re.search(
        r"(?ims)^\s*Strengths:\s*(.*?)(?=^\s*Improvements:|\Z)",
        feedback,
    )
    if strengths_match:
        metadata["strengths"] = _parse_bullets(strengths_match.group(1))

    improvements_match = re.search(r"(?ims)^\s*Improvements:\s*(.*)\Z", feedback)
    if improvements_match:
        metadata["improvements"] = _parse_bullets(improvements_match.group(1))

    return metadata


def get_next_practice_attempt_number(
    db: Session,
    user_id: int,
    lesson_id: str,
    step_index: int,
) -> int:
    max_attempt_number = (
        db.query(func.max(models.PracticeSubmission.attempt_number))
        .filter(
            models.PracticeSubmission.user_id == user_id,
            models.PracticeSubmission.lesson_id == lesson_id,
            models.PracticeSubmission.step_index == step_index,
        )
        .scalar()
    )
    return (max_attempt_number or 0) + 1


async def stream_lesson_ai_response(
    db: Session,
    *,
    openai_input: list[dict[str, str]],
    lesson_id: str,
    user_id: int,
    stream_name: str,
    is_disconnected: DisconnectCallable,
    stream_text: chat_service.StreamTextCallable = chat_service.stream_openai_text,
):
    try:
        try:
            async for chunk in stream_text(openai_input):
                if await is_disconnected():
                    logger.info(
                        f"Client disconnected from lesson {stream_name} stream",
                        extra={"lesson_id": lesson_id, "user_id": user_id},
                    )
                    return
                if chunk:
                    yield chat_service.format_sse_data(chunk)
        except AuthenticationError:
            logger.exception(f"OpenAI authentication failed during lesson {stream_name} stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APITimeoutError:
            logger.exception(f"OpenAI request timed out during lesson {stream_name} stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APIConnectionError:
            logger.exception(f"OpenAI network connection failed during lesson {stream_name} stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APIStatusError:
            logger.exception(f"OpenAI API returned an error status during lesson {stream_name} stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APIError:
            logger.exception(f"OpenAI API error during lesson {stream_name} stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except OpenAIError:
            logger.exception(f"OpenAI error during lesson {stream_name} stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except Exception:
            logger.exception(f"Unexpected error during lesson {stream_name} stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
    finally:
        db.close()


async def stream_practice_feedback_response(
    db: Session,
    *,
    openai_input: list[dict[str, str]],
    lesson: dict,
    step_index: int,
    user_id: int,
    clean_answer: str,
    is_disconnected: DisconnectCallable,
    stream_text: chat_service.StreamTextCallable = chat_service.stream_openai_text,
):
    chunks: list[str] = []
    lesson_id = lesson["lesson_id"]
    try:
        try:
            async for chunk in stream_text(openai_input):
                if await is_disconnected():
                    logger.info(
                        "Client disconnected from lesson practice feedback stream",
                        extra={"lesson_id": lesson_id, "user_id": user_id},
                    )
                    return
                if chunk:
                    chunks.append(chunk)
                    yield chat_service.format_sse_data(chunk)
        except AuthenticationError:
            logger.exception("OpenAI authentication failed during practice feedback stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APITimeoutError:
            logger.exception("OpenAI request timed out during practice feedback stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APIConnectionError:
            logger.exception("OpenAI network connection failed during practice feedback stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APIStatusError:
            logger.exception("OpenAI API returned an error status during practice feedback stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APIError:
            logger.exception("OpenAI API error during practice feedback stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except OpenAIError:
            logger.exception("OpenAI error during practice feedback stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except Exception:
            logger.exception("Unexpected error during practice feedback stream")
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return

        feedback = "".join(chunks).strip()
        if not feedback:
            return
        metadata = parse_practice_feedback_metadata(feedback)

        db.add(
            models.PracticeSubmission(
                user_id=user_id,
                lesson_id=lesson_id,
                step_index=step_index,
                attempt_number=get_next_practice_attempt_number(
                    db,
                    user_id,
                    lesson_id,
                    step_index,
                ),
                answer=clean_answer,
                feedback=feedback,
                score=metadata["score"],
                strengths=metadata["strengths"],
                improvements=metadata["improvements"],
            )
        )
        db.commit()
    finally:
        db.close()
