import logging
from fastapi import (
    APIRouter, Depends, HTTPException,
    Response, Query
)
from typing import List, Optional

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
from ..models import EntityType

router = APIRouter(tags=["courses"])
logger = logging.getLogger(__name__)


# <editor-fold desc="CourseTerm endpoints">
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


# </editor-fold>

# <editor-fold desc="Course endpoints">
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
    logger.info(f"{current_user.username} updating course {course_id} → {c_in}")

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


# </editor-fold>

# <editor-fold desc="Course-related institutions endpoints">
# — Institutions —

@router.get("/courses/{course_id}/institutions/", response_model=List[schemas.InstitutionRead])
def list_course_institutions(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing institutions for course {course_id}")
    return crud.get_course_institutions(db, course_id)


@router.post("/courses/{course_id}/institutions/", response_model=schemas.InstitutionRead)
def add_course_institution(
    course_id: int,
    link: schemas.CourseInstitutionLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking institution "
                f"{link.institution_id} → course {course_id}")
    try:
        return crud.add_institution_to_course(db, course_id, link.institution_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/courses/{course_id}/institutions/{institution_id}", status_code=204)
def remove_course_institution(
    course_id: int,
    institution_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking institution "
                f"{institution_id} from course {course_id}")
    try:
        crud.remove_institution_from_course(db, course_id, institution_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Course-related teachers endpoints">
# — Teachers —

@router.get("/courses/{course_id}/teachers/", response_model=List[schemas.PersonRoleReadFull])
def list_course_teachers(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing teachers for course {course_id}")
    return crud.get_course_teachers(db, course_id)


@router.post("/courses/{course_id}/teachers/", response_model=schemas.PersonRoleReadFull)
def add_course_teacher(
    course_id: int,
    link: schemas.CourseTeacherLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking person role (teacher) "
                f"{link.person_role_id} → course {course_id}")
    try:
        return crud.add_teacher_to_course(db, course_id, link.person_role_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/courses/{course_id}/teachers/{person_role_id}", status_code=204)
def remove_course_teacher(
    course_id: int,
    person_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking person role (teacher) "
                f"{person_role_id} from course {course_id}")
    try:
        crud.remove_teacher_from_course(db, course_id, person_role_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Course-related students endpoints">
# — Students —

@router.get("/courses/{course_id}/students/", response_model=List[schemas.CourseStudentRead])
def list_course_students(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing phd students for course {course_id}")
    return crud.get_course_students(db, course_id)


@router.post("/courses/{course_id}/students/", response_model=schemas.CourseStudentRead)
def add_course_student(
    course_id: int,
    link: schemas.CourseStudentLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking phd student "
                f"{link.phd_student_id} → course {course_id}")
    try:
        return crud.add_student_to_course(db, course_id, link)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/courses/{course_id}/students/{phd_student_id}", response_model=schemas.CourseStudentRead)
def update_course_student(
    course_id: int,
    phd_student_id: int,
    link: schemas.CourseStudentLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating course‐student link: phd student "
                f"{phd_student_id} for course {course_id} → {link}")
    try:
        return crud.update_student_course_link(db, course_id, phd_student_id, link)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/courses/{course_id}/students/{phd_student_id}", status_code=204)
def remove_course_student(
    course_id: int,
    phd_student_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking phd student "
                f"{phd_student_id} from course {course_id}")
    try:
        crud.remove_student_from_course(db, course_id, phd_student_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Course-related decision letters endpoints">
# — Decision Letters —

@router.get("/courses/{cid}/decision-letters/", response_model=List[schemas.DecisionLetterRead])
def course_decision_letters(cid: int, db: Session = Depends(dependencies.get_db),
                            current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} listed decision letters for course {cid}")
    return crud.list_decision_letters(db, EntityType.COURSE, cid)


@router.post("/courses/{cid}/decision-letters/", response_model=schemas.DecisionLetterRead)
def add_course_decision_letter(cid: int, dl_in: schemas.DecisionLetterCreate,
                               db: Session = Depends(dependencies.get_db),
                               current_user=Depends(dependencies.get_current_user)):
    if not crud.get_course(db, cid):
        logger.warning(f"Course #{cid} not found")
        raise HTTPException(404, f"Course #{cid} not found")
    logger.info(f"{current_user.username} adding decision letter {dl_in.link} for course {cid}")
    return crud.add_decision_letter(db, EntityType.COURSE, cid, dl_in.link)


@router.put("/courses/{cid}/decision-letters/{dlid}", response_model=schemas.DecisionLetterRead)
def update_course_decision_letter(
    cid: int, dlid: int,
    dl_in: schemas.DecisionLetterUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating decision letter {dlid} → {dl_in} for course {cid}")

    try:
        return crud.update_decision_letter(db, dlid, dl_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/courses/{cid}/decision-letters/{dlid}", status_code=204)
def del_course_decision_letter(cid: int, dlid: int,
                               db: Session = Depends(dependencies.get_db),
                               current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} removing decision letter {dlid} for course {cid}")
    crud.remove_decision_letter(db, dlid)
    return Response(status_code=204)


# </editor-fold>
