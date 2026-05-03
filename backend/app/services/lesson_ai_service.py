import json
import logging
import os
import time
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
from app.observability import get_request_id, reset_request_id, set_request_id
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
                "Be supportive and not harsh.\n"
                "Do not invent requirements outside the lesson.\n"
                "Return only a valid JSON object with this exact structure:\n"
                "{\n"
                '  "score": 0,\n'
                '  "strengths": ["..."],\n'
                '  "improvements": ["..."],\n'
                '  "suggested_answer": "...",\n'
                '  "summary_feedback": "..."\n'
                "}\n"
                "score must be an integer from 0 to 100.\n"
                "strengths and improvements must be arrays of concise strings.\n"
                "suggested_answer must be one improved answer.\n"
                "summary_feedback must be concise learner-facing feedback.\n"
                "Do not wrap the JSON in Markdown. Do not include any text outside the JSON object."
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


def _empty_practice_feedback_metadata() -> dict[str, int | list[str] | str | None]:
    return {
        "score": None,
        "strengths": None,
        "improvements": None,
        "suggested_answer": None,
        "summary_feedback": None,
    }


def _strip_json_code_fence(value: str) -> str:
    clean_value = value.strip()
    if not clean_value.startswith("```") or not clean_value.endswith("```"):
        return clean_value

    lines = clean_value.splitlines()
    if len(lines) < 3:
        return clean_value

    return "\n".join(lines[1:-1]).strip()


def _clean_string_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None

    clean_items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return clean_items or None


def _clean_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    clean_value = value.strip()
    return clean_value or None


def parse_practice_feedback_metadata(feedback: str) -> dict[str, int | list[str] | str | None]:
    try:
        payload = json.loads(_strip_json_code_fence(feedback))
    except json.JSONDecodeError:
        return _empty_practice_feedback_metadata()

    if not isinstance(payload, dict):
        return _empty_practice_feedback_metadata()

    raw_score = payload.get("score")
    score = raw_score if isinstance(raw_score, int) and not isinstance(raw_score, bool) else None
    if score is None or score < 0 or score > 100:
        score = None

    return {
        "score": score,
        "strengths": _clean_string_list(payload.get("strengths")),
        "improvements": _clean_string_list(payload.get("improvements")),
        "suggested_answer": _clean_string(
            payload.get("suggested_answer", payload.get("corrected_answer"))
        ),
        "summary_feedback": _clean_string(payload.get("summary_feedback")),
    }


def format_practice_feedback_for_user(
    metadata: dict[str, int | list[str] | str | None],
    fallback_feedback: str,
) -> str:
    summary_feedback = metadata.get("summary_feedback")
    suggested_answer = metadata.get("suggested_answer")
    strengths = metadata.get("strengths")
    improvements = metadata.get("improvements")
    score = metadata.get("score")

    if not any([summary_feedback, suggested_answer, strengths, improvements, score is not None]):
        return fallback_feedback

    lines: list[str] = []
    if summary_feedback:
        lines.append(str(summary_feedback))

    if suggested_answer:
        if lines:
            lines.append("")
        lines.extend(["Suggested answer:", str(suggested_answer)])

    if strengths:
        if lines:
            lines.append("")
        lines.append("Strengths:")
        lines.extend(f"- {item}" for item in strengths)

    if improvements:
        if lines:
            lines.append("")
        lines.append("Improvements:")
        lines.extend(f"- {item}" for item in improvements)

    if score is not None:
        if lines:
            lines.append("")
        lines.append(f"Score: {score}/100")

    return "\n".join(lines).strip()


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
    request_id: str | None = None,
):
    started_at = time.perf_counter()
    model = os.getenv("OPENAI_MODEL", chat_service.OPENAI_MODEL)
    outcome = "success"
    request_id = request_id or get_request_id()
    request_id_token = set_request_id(request_id)
    logger.info(
        "lesson_stream.start",
        extra={
            "request_id": request_id,
            "lesson_id": lesson_id,
            "user_id": user_id,
            "model": model,
            "stream_name": stream_name,
        },
    )
    try:
        try:
            async for chunk in stream_text(openai_input):
                if await is_disconnected():
                    outcome = "disconnected"
                    logger.info(
                        "lesson_stream.disconnected",
                        extra={
                            "request_id": request_id,
                            "lesson_id": lesson_id,
                            "user_id": user_id,
                            "model": model,
                            "stream_name": stream_name,
                            "stream_outcome": outcome,
                        },
                    )
                    return
                if chunk:
                    yield chat_service.format_sse_data(chunk)
        except AuthenticationError:
            outcome = "error"
            logger.exception(
                "lesson_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_name": stream_name,
                    "stream_outcome": outcome,
                    "reason": "openai_authentication_failed",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APITimeoutError:
            outcome = "error"
            logger.exception(
                "lesson_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_name": stream_name,
                    "stream_outcome": outcome,
                    "reason": "openai_timeout",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APIConnectionError:
            outcome = "error"
            logger.exception(
                "lesson_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_name": stream_name,
                    "stream_outcome": outcome,
                    "reason": "openai_connection_failed",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APIStatusError:
            outcome = "error"
            logger.exception(
                "lesson_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_name": stream_name,
                    "stream_outcome": outcome,
                    "reason": "openai_status_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except APIError:
            outcome = "error"
            logger.exception(
                "lesson_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_name": stream_name,
                    "stream_outcome": outcome,
                    "reason": "openai_api_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except OpenAIError:
            outcome = "error"
            logger.exception(
                "lesson_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_name": stream_name,
                    "stream_outcome": outcome,
                    "reason": "openai_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
        except Exception:
            outcome = "error"
            logger.exception(
                "lesson_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_name": stream_name,
                    "stream_outcome": outcome,
                    "reason": "unexpected_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
    finally:
        logger.info(
            "lesson_stream.end",
            extra={
                "request_id": request_id,
                "lesson_id": lesson_id,
                "user_id": user_id,
                "model": model,
                "stream_name": stream_name,
                "stream_outcome": outcome,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        reset_request_id(request_id_token)
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
    request_id: str | None = None,
):
    chunks: list[str] = []
    lesson_id = lesson["lesson_id"]
    started_at = time.perf_counter()
    model = os.getenv("OPENAI_MODEL", chat_service.OPENAI_MODEL)
    outcome = "empty"
    request_id = request_id or get_request_id()
    request_id_token = set_request_id(request_id)
    logger.info(
        "practice_stream.start",
        extra={
            "request_id": request_id,
            "lesson_id": lesson_id,
            "user_id": user_id,
            "model": model,
            "step_index": step_index,
        },
    )
    try:
        try:
            async for chunk in stream_text(openai_input):
                if await is_disconnected():
                    outcome = "disconnected"
                    logger.info(
                        "practice_stream.disconnected",
                        extra={
                            "request_id": request_id,
                            "lesson_id": lesson_id,
                            "user_id": user_id,
                            "model": model,
                            "step_index": step_index,
                            "stream_outcome": outcome,
                        },
                    )
                    return
                if chunk:
                    chunks.append(chunk)
        except AuthenticationError:
            outcome = "error"
            logger.exception(
                "practice_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "step_index": step_index,
                    "stream_outcome": outcome,
                    "reason": "openai_authentication_failed",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APITimeoutError:
            outcome = "error"
            logger.exception(
                "practice_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "step_index": step_index,
                    "stream_outcome": outcome,
                    "reason": "openai_timeout",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APIConnectionError:
            outcome = "error"
            logger.exception(
                "practice_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "step_index": step_index,
                    "stream_outcome": outcome,
                    "reason": "openai_connection_failed",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APIStatusError:
            outcome = "error"
            logger.exception(
                "practice_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "step_index": step_index,
                    "stream_outcome": outcome,
                    "reason": "openai_status_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except APIError:
            outcome = "error"
            logger.exception(
                "practice_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "step_index": step_index,
                    "stream_outcome": outcome,
                    "reason": "openai_api_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except OpenAIError:
            outcome = "error"
            logger.exception(
                "practice_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "step_index": step_index,
                    "stream_outcome": outcome,
                    "reason": "openai_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return
        except Exception:
            outcome = "error"
            logger.exception(
                "practice_stream.error",
                extra={
                    "request_id": request_id,
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                    "model": model,
                    "step_index": step_index,
                    "stream_outcome": outcome,
                    "reason": "unexpected_error",
                },
            )
            yield chat_service.format_sse_data(chat_service.SAFE_STREAM_ERROR)
            return

        raw_feedback = "".join(chunks).strip()
        if not raw_feedback:
            return
        metadata = parse_practice_feedback_metadata(raw_feedback)
        feedback = format_practice_feedback_for_user(metadata, raw_feedback)
        yield chat_service.format_sse_data(feedback)

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
        outcome = "success"
        db.commit()
    finally:
        logger.info(
            "practice_stream.end",
            extra={
                "request_id": request_id,
                "lesson_id": lesson_id,
                "user_id": user_id,
                "model": model,
                "step_index": step_index,
                "stream_outcome": outcome,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        reset_request_id(request_id_token)
        db.close()
