from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, lessons, models, progress as progress_service, schemas
from app.database import get_db
from app.services import chat_service, lesson_ai_service


router = APIRouter(prefix="/lessons", tags=["lessons"])

THEORY_STEP_XP = {
    "intro": 5,
    "concept": 10,
    "deep_dive": 15,
    "explanation": 10,
    "example": 10,
    "checklist": 10,
    "summary": 5,
    "article": 20,
}

READING_STEP_TYPES = set(THEORY_STEP_XP)
STUDY_ACTIONS = lesson_ai_service.STUDY_ACTIONS

build_lesson_tutor_prompt = lesson_ai_service.build_lesson_tutor_prompt
build_lesson_study_prompt = lesson_ai_service.build_lesson_study_prompt
build_practice_feedback_prompt = lesson_ai_service.build_practice_feedback_prompt
parse_practice_feedback_metadata = lesson_ai_service.parse_practice_feedback_metadata
get_next_practice_attempt_number = lesson_ai_service.get_next_practice_attempt_number
_stream_openai_text = chat_service.stream_openai_text


def get_reading_steps_for_study(lesson: dict, step_index: int | None = None) -> list[dict]:
    return lesson_ai_service.get_reading_steps_for_study(
        lesson,
        READING_STEP_TYPES,
        step_index,
    )


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


def get_lesson_step_progress_map(
    db: Session,
    user_id: int,
    lesson_id: str,
) -> dict[int, models.LessonStepProgress]:
    rows = (
        db.query(models.LessonStepProgress)
        .filter(
            models.LessonStepProgress.user_id == user_id,
            models.LessonStepProgress.lesson_id == lesson_id,
        )
        .all()
    )
    return {row.step_index: row for row in rows}


def serialize_lesson(
    lesson: dict,
    progress: models.LessonProgress,
    step_progress_by_index: dict[int, models.LessonStepProgress] | None = None,
) -> schemas.LessonRead:
    step_progress_by_index = step_progress_by_index or {}
    steps = []
    for index, step in enumerate(lesson["steps"]):
        step_progress = step_progress_by_index.get(index)
        steps.append(
            {
                **step,
                "completed": bool(step_progress.completed) if step_progress else False,
                "completed_at": step_progress.completed_at if step_progress else None,
                "xp_awarded": step_progress.xp_awarded if step_progress else 0,
            }
        )

    return schemas.LessonRead(
        lesson_id=lesson["lesson_id"],
        course_id=lesson["course_id"],
        title=lesson["title"],
        difficulty=lesson.get("difficulty"),
        steps=steps,
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


def get_or_create_lesson_step_progress(
    db: Session,
    user_id: int,
    lesson_id: str,
    step_index: int,
    step_type: str,
) -> models.LessonStepProgress:
    step_progress = (
        db.query(models.LessonStepProgress)
        .filter(
            models.LessonStepProgress.user_id == user_id,
            models.LessonStepProgress.lesson_id == lesson_id,
            models.LessonStepProgress.step_index == step_index,
        )
        .first()
    )
    if step_progress:
        return step_progress

    step_progress = models.LessonStepProgress(
        user_id=user_id,
        lesson_id=lesson_id,
        step_index=step_index,
        step_type=step_type,
    )
    db.add(step_progress)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        step_progress = (
            db.query(models.LessonStepProgress)
            .filter(
                models.LessonStepProgress.user_id == user_id,
                models.LessonStepProgress.lesson_id == lesson_id,
                models.LessonStepProgress.step_index == step_index,
            )
            .one()
        )
    return step_progress


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
    step_progress_by_index = get_lesson_step_progress_map(
        db,
        current_user.id,
        lesson["lesson_id"],
    )
    return serialize_lesson(lesson, lesson_progress, step_progress_by_index)


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
    step_progress_by_index = get_lesson_step_progress_map(
        db,
        current_user.id,
        lesson["lesson_id"],
    )
    return serialize_lesson(lesson, lesson_progress, step_progress_by_index)


@router.post("/{lesson_id}/steps/{step_index}/complete", response_model=schemas.LessonRead)
def complete_lesson_step(
    lesson_id: str,
    step_index: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id)
    step = resolve_lesson_step(lesson, None, step_index)
    lesson_progress = get_or_create_lesson_progress(db, current_user.id, lesson)
    step_progress = get_or_create_lesson_step_progress(
        db,
        current_user.id,
        lesson["lesson_id"],
        step_index,
        step["type"],
    )

    if not step_progress.completed:
        step_progress.completed = True
        step_progress.completed_at = datetime.now(timezone.utc)
        step_progress.step_type = step["type"]
        xp_award = THEORY_STEP_XP.get(step["type"], 0)
        step_progress.xp_awarded = xp_award
        if xp_award:
            progress_service.award_xp(db, current_user.id, xp_award)

    db.commit()
    db.refresh(lesson_progress)
    step_progress_by_index = get_lesson_step_progress_map(
        db,
        current_user.id,
        lesson["lesson_id"],
    )
    return serialize_lesson(lesson, lesson_progress, step_progress_by_index)


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

    return StreamingResponse(
        lesson_ai_service.stream_lesson_ai_response(
            db,
            openai_input=openai_input,
            lesson_id=lesson_id,
            user_id=current_user.id,
            stream_name="tutor",
            is_disconnected=request.is_disconnected,
            stream_text=_stream_openai_text,
        ),
        media_type="text/event-stream",
    )


@router.get("/{lesson_id}/study-stream")
async def lesson_study_stream(
    request: Request,
    lesson_id: str,
    action: str,
    question: str | None = Query(default=None),
    step_index: int | None = Query(default=None),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    if action not in STUDY_ACTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid study action")

    clean_question = (question or "").strip()
    if action == "custom_question" and not clean_question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty")

    current_user = auth.get_user_from_token(db, token)
    lesson = get_lesson_or_404(lesson_id)
    reading_steps = get_reading_steps_for_study(lesson, step_index)
    openai_input = build_lesson_study_prompt(
        lesson,
        reading_steps,
        action,
        clean_question,
    )

    return StreamingResponse(
        lesson_ai_service.stream_lesson_ai_response(
            db,
            openai_input=openai_input,
            lesson_id=lesson_id,
            user_id=current_user.id,
            stream_name="study",
            is_disconnected=request.is_disconnected,
            stream_text=_stream_openai_text,
        ),
        media_type="text/event-stream",
    )


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

    return StreamingResponse(
        lesson_ai_service.stream_practice_feedback_response(
            db,
            openai_input=openai_input,
            lesson=lesson,
            step_index=step_index,
            user_id=current_user.id,
            clean_answer=clean_answer,
            is_disconnected=request.is_disconnected,
            stream_text=_stream_openai_text,
        ),
        media_type="text/event-stream",
    )


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
