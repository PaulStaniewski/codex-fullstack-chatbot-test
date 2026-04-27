from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, lessons, models, progress as progress_service, schemas
from app.database import get_db


router = APIRouter(prefix="/lessons", tags=["lessons"])


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
