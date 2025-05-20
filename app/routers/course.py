import logging
from fastapi import (
    APIRouter, Depends, HTTPException,
    Response, Query
)
from typing import List, Optional

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError

router = APIRouter(tags=["courses"])
logger = logging.getLogger(__name__)


# --- CourseTerm endpoints ---
@router.get("/course-terms/{term_id}", response_model=schemas.CourseTermRead)
def read_term(
    term_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    t = crud.get_course_term(db, term_id)
    if not t:
        logger.warning(f"Course term #{term_id} not found")
        raise HTTPException(404, f"CourseTerm #{term_id} not found")

    logger.info(f"{current_user.username} fetched course term '{t.season} {t.year}'")

    return t


@router.get("/course-terms/", response_model=List[schemas.CourseTermRead])
def list_terms(
    active: Optional[bool] = Query(None),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed course terms (active={active})")
    return crud.list_course_terms(db, active=active)


@router.post("/course-terms/next", response_model=schemas.CourseTermRead)
def create_next_term(
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} creating next course term")
    return crud.create_next_course_term(db)


@router.put("/course-terms/{term_id}", response_model=schemas.CourseTermRead)
def update_term(
    term_id: int,
    term_in: schemas.CourseTermUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating course term {term_id} → {term_in}")

    try:
        return crud.update_course_term(db, term_id, term_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/course-terms/{term_id}", status_code=204)
def delete_term(
    term_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} deleting course term {term_id}")

    try:
        crud.delete_course_term(db, term_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# --- Course endpoints ---
@router.get("/courses/{course_id}", response_model=schemas.CourseRead)
def read_course(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    c = crud.get_course(db, course_id)
    if not c:
        logger.warning(f"Course #{course_id} not found")
        raise HTTPException(404, f"Course #{course_id} not found")

    logger.info(f"{current_user.username} fetched course [{c.id}] '{c.title}'")

    return c


@router.get("/courses/", response_model=List[schemas.CourseRead])
def list_courses(
    title:     Optional[str] = Query(None),
    term_id:   Optional[int] = Query(None, ge=1),
    activity_id: Optional[int] = Query(None, ge=1),
    search:    Optional[str] = Query(None),
    db:         Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed courses (title={title}, term_id={term_id}, "
                f"activity_id={activity_id}, search={search!r})")
    return crud.list_courses(
        db,
        title=title,
        term_id=term_id,
        activity_id=activity_id,
        search=search
    )


@router.post("/courses/", response_model=schemas.CourseRead)
def create_course(
    c_in: schemas.CourseCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} creating course {c_in.title}")
    try:
        return crud.create_course(db, c_in)
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/courses/{course_id}", response_model=schemas.CourseRead)
def update_course(
    course_id: int,
    c_in: schemas.CourseUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating institution {course_id} → {c_in}")

    try:
        return crud.update_course(db, course_id, c_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} deleting course {course_id}")

    try:
        crud.delete_course(db, course_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)
