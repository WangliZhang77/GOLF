from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.course import Course
from app.models.user import User, UserRole
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate

router = APIRouter(prefix="/courses", tags=["course"])

_MANAGE_ROLES = {UserRole.super_admin, UserRole.council_admin, UserRole.event_director}


def _get_course(db: Session, course_id: int) -> Course:
    c = (
        db.query(Course)
        .filter(Course.id == course_id, Course.is_deleted.is_(False))
        .first()
    )
    if c is None:
        raise HTTPException(status_code=404, detail="球场不存在 / Course not found")
    return c


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    course = Course(**payload.model_dump(), created_by=current_user.id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("", response_model=list[CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Course)
        .filter(Course.is_deleted.is_(False))
        .order_by(Course.id)
        .all()
    )


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_course(db, course_id)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    course = _get_course(db, course_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    course.updated_by = current_user.id
    db.commit()
    db.refresh(course)
    return course
