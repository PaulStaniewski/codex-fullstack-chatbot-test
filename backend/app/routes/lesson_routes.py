import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAIError,
)
from sqlalchemy.orm import Session

from app import auth, lessons, models, progress as progress_service, schemas
from app.database import get_db
from app.routes.chat_routes import SAFE_STREAM_ERROR, _format_sse_data, _stream_openai_text


router = APIRouter(prefix="/lessons", tags=["lessons"])
logger = logging.getLogger(__name__)


def get_lesson_or_404(lesson_id: str) -> dict:
    lesson = lessons.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson


def get_or_create_lesson_progress(
    db: Session,
    user_id: int,
    lesson: dict,
) -> models.LessonProgress:
    progress = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.user_id == user_id,
            models.LessonProgress.lesson_id == lesson["lesson_id"],
        )
        .first()
    )
    if progress:
        return progress

    progress = models.LessonProgress(
        user_id=user_id,
        lesson_id=lesson["lesson_id"],
        course_id=lesson["course_id"],
    )
    db.add(progress)
    db.flush()
    return progress


def serialize_lesson(lesson: dict, progress: models.LessonProgress) -> schemas.LessonRead:
    return schemas.LessonRead(
        lesson_id=lesson["lesson_id"],
        course_id=lesson["course_id"],
        title=lesson["title"],
        steps=lesson["steps"],
        current_step_index=progress.current_step_index,
        completed=progress.completed,
        completed_at=progress.completed_at,
    )


def resolve_lesson_step(
    lesson: dict,
    progress: models.LessonProgress | None,
    step_index: int | None,
) -> dict:
    resolved_step_index = progress.current_step_index if step_index is None and progress else step_index
    if resolved_step_index is None:
        resolved_step_index = 0

    if resolved_step_index < 0 or resolved_step_index >= len(lesson["steps"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid step index")

    return lesson["steps"][resolved_step_index]


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


@router.get("/progress", response_model=list[schemas.LessonProgressRead])
def list_lesson_progress(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.LessonProgress)
        .filter(models.LessonProgress.user_id == current_user.id)
        .order_by(models.LessonProgress.updated_at.desc())
        .all()
    )


@router.get("/{lesson_id}", response_model=schemas.LessonRead)
def get_lesson(
    lesson_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id)
    lesson_progress = get_or_create_lesson_progress(db, current_user.id, lesson)
    db.commit()
    db.refresh(lesson_progress)
    return serialize_lesson(lesson, lesson_progress)


@router.post("/{lesson_id}/next", response_model=schemas.LessonRead)
def next_lesson_step(
    lesson_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id)
    lesson_progress = get_or_create_lesson_progress(db, current_user.id, lesson)

    if not lesson_progress.completed:
        last_step_index = len(lesson["steps"]) - 1
        if lesson_progress.current_step_index >= last_step_index:
            lesson_progress.completed = True
            lesson_progress.completed_at = datetime.now(timezone.utc)
            progress_service.award_lesson_completion_xp(db, current_user.id)
        else:
            lesson_progress.current_step_index += 1

    db.commit()
    db.refresh(lesson_progress)
    return serialize_lesson(lesson, lesson_progress)


@router.get("/{lesson_id}/tutor-stream")
async def lesson_tutor_stream(
    request: Request,
    lesson_id: str,
    question: str,
    step_index: int | None = Query(default=None),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    clean_question = question.strip()
    if not clean_question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty")

    current_user = auth.get_user_from_token(db, token)
    lesson = get_lesson_or_404(lesson_id)
    lesson_progress = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.user_id == current_user.id,
            models.LessonProgress.lesson_id == lesson["lesson_id"],
        )
        .first()
    )
    step = resolve_lesson_step(lesson, lesson_progress, step_index)
    openai_input = build_lesson_tutor_prompt(lesson, step, clean_question)

    async def event_generator():
        try:
            try:
                async for chunk in _stream_openai_text(openai_input):
                    if await request.is_disconnected():
                        logger.info(
                            "Client disconnected from lesson tutor stream",
                            extra={"lesson_id": lesson_id, "user_id": current_user.id},
                        )
                        return
                    if chunk:
                        yield _format_sse_data(chunk)
            except AuthenticationError:
                logger.exception("OpenAI authentication failed during lesson tutor stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
            except APITimeoutError:
                logger.exception("OpenAI request timed out during lesson tutor stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
            except APIConnectionError:
                logger.exception("OpenAI network connection failed during lesson tutor stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
            except APIStatusError:
                logger.exception("OpenAI API returned an error status during lesson tutor stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
            except APIError:
                logger.exception("OpenAI API error during lesson tutor stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
            except OpenAIError:
                logger.exception("OpenAI error during lesson tutor stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
            except Exception:
                logger.exception("Unexpected error during lesson tutor stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
        finally:
            db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{lesson_id}/practice-feedback-stream")
async def lesson_practice_feedback_stream(
    request: Request,
    lesson_id: str,
    step_index: int,
    answer: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    clean_answer = answer.strip()
    if not clean_answer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Answer cannot be empty")

    current_user = auth.get_user_from_token(db, token)
    lesson = get_lesson_or_404(lesson_id)
    step = resolve_lesson_step(lesson, None, step_index)
    if step["type"] != "practice":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Practice feedback is only available for practice steps",
        )

    openai_input = build_practice_feedback_prompt(lesson, step, clean_answer)

    async def event_generator():
        chunks: list[str] = []
        try:
            try:
                async for chunk in _stream_openai_text(openai_input):
                    if await request.is_disconnected():
                        logger.info(
                            "Client disconnected from lesson practice feedback stream",
                            extra={"lesson_id": lesson_id, "user_id": current_user.id},
                        )
                        return
                    if chunk:
                        chunks.append(chunk)
                        yield _format_sse_data(chunk)
            except AuthenticationError:
                logger.exception("OpenAI authentication failed during practice feedback stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APITimeoutError:
                logger.exception("OpenAI request timed out during practice feedback stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APIConnectionError:
                logger.exception("OpenAI network connection failed during practice feedback stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APIStatusError:
                logger.exception("OpenAI API returned an error status during practice feedback stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APIError:
                logger.exception("OpenAI API error during practice feedback stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except OpenAIError:
                logger.exception("OpenAI error during practice feedback stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except Exception:
                logger.exception("Unexpected error during practice feedback stream")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return

            feedback = "".join(chunks).strip()
            if not feedback:
                return
            metadata = parse_practice_feedback_metadata(feedback)

            db.add(
                models.PracticeSubmission(
                    user_id=current_user.id,
                    lesson_id=lesson["lesson_id"],
                    step_index=step_index,
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{lesson_id}/practice-history", response_model=list[schemas.PracticeSubmissionRead])
def get_practice_history(
    lesson_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_lesson_or_404(lesson_id)
    return (
        db.query(models.PracticeSubmission)
        .filter(
            models.PracticeSubmission.user_id == current_user.id,
            models.PracticeSubmission.lesson_id == lesson_id,
        )
        .order_by(models.PracticeSubmission.created_at.desc(), models.PracticeSubmission.id.desc())
        .all()
    )
