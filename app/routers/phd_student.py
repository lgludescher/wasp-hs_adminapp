import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError, StudentActivityNotFound
from ..models import ActivityType

router = APIRouter(tags=["phd_students"])
logger = logging.getLogger(__name__)


# <editor-fold desc="PhdStudent endpoints">
# --- PhDStudent endpoints ---

@router.get("/phd-students/{stu_id}", response_model=schemas.PhDStudentRead)
def read_phd_student(
    stu_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    s = crud.get_phd_student(db, stu_id)
    if not s:
        logger.warning(f"PhDStudent #{stu_id} not found")
        raise HTTPException(404, f"PhDStudent #{stu_id} not found")
    logger.info(f"{current_user.username} fetched phd_student #{stu_id}")
    return s


@router.get("/phd-students/", response_model=List[schemas.PhDStudentRead])
def list_phd_students(
    person_role_id:   Optional[int] = Query(None, ge=1, description="Filter by person_role_id"),
    is_active:        Optional[bool] = Query(None, description="Only active/inactive roles"),
    cohort_number:    Optional[int] = Query(None, ge=0, description="Filter by cohort number"),
    is_affiliated:    Optional[bool] = Query(None, description="Filter by affiliation status"),
    is_graduated:     Optional[bool] = Query(None, description="Filter by graduation status"),
    institution_id:   Optional[int] = Query(None, ge=1, description="Filter by institution"),
    field_id:         Optional[int] = Query(None, ge=1, description="Filter by academic field"),
    branch_id:        Optional[int] = Query(None, ge=1, description="Filter by academic branch"),
    search:           Optional[str] = Query(None, description="Substring search on person name"),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(
        f"{current_user.username} listed PhD students "
        f"(person_role_id={person_role_id}, is_active={is_active}, cohort={cohort_number}, "
        f"is_affiliated={is_affiliated}, is_graduated={is_graduated}, "
        f"institution_id={institution_id}, field_id={field_id}, branch_id={branch_id}, search={search!r})"
    )
    return crud.list_phd_students(
        db,
        person_role_id=person_role_id,
        is_active=is_active,
        cohort_number=cohort_number,
        is_affiliated=is_affiliated,
        is_graduated=is_graduated,
        institution_id=institution_id,
        field_id=field_id,
        branch_id=branch_id,
        search=search,
    )


@router.post("/phd-students/", response_model=schemas.PhDStudentRead)
def create_phd_student(
    s_in: schemas.PhDStudentCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating phd_student {s_in}")
    try:
        return crud.create_phd_student(db, s_in)
    except Exception as e:
        logger.warning(f"Failed to create phd_student: {e}")
        raise HTTPException(400, str(e))


@router.put("/phd-students/{stu_id}", response_model=schemas.PhDStudentRead)
def update_phd_student(
    stu_id: int,
    s_in: schemas.PhDStudentUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating phd_student #{stu_id} → {s_in}")
    try:
        return crud.update_phd_student(db, stu_id, s_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/phd-students/{stu_id}", status_code=204)
def delete_phd_student(
    stu_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting phd_student #{stu_id}")
    try:
        crud.delete_phd_student(db, stu_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="StudentActivity endpoints">
# --- StudentActivity endpoints ---

@router.get("/phd-students/{stu_id}/activities/", response_model=List[schemas.StudentActivityRead])
def list_student_activities(
    stu_id: int,
    activity_type: Optional[ActivityType] = Query(
        None,
        description="Filter by activity type (GRAD_SCHOOL or ABROAD)"
    ),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    # Verify the student exists
    from ..crud import get_phd_student
    if not get_phd_student(db, stu_id):
        logger.warning(f"PhDStudent #{stu_id} not found")
        raise HTTPException(404, f"PhDStudent #{stu_id} not found")

    logger.info(
        f"{current_user.username} listing activities for phd_student #{stu_id}"
        f"{' of type ' + activity_type.value if activity_type else ''}"
    )

    return crud.list_student_activities(db, phd_student_id=stu_id, activity_type=activity_type)


@router.post("/phd-students/{stu_id}/activities/grad-school", response_model=schemas.StudentActivityRead)
def create_grad_school_activity_for_student(
    stu_id:   int,
    in_data:  schemas.GradSchoolStudentActivityCreate,
    current_user=Depends(dependencies.get_current_user),
    db:       Session = Depends(dependencies.get_db),
):
    # if in_data.activity_type.name != "GRAD_SCHOOL":
    #     raise HTTPException(400, "activity_type must be GRAD_SCHOOL")

    logger.info(f"{current_user.username} creating GRAD_SCHOOL activity for student {stu_id}: {in_data}")

    try:
        new_act = crud.create_grad_school_student_activity(db, stu_id, in_data)
        return new_act
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.post("/phd-students/{stu_id}/activities/abroad", response_model=schemas.StudentActivityRead)
def create_abroad_activity_for_student(
    stu_id:   int,
    in_data:  schemas.AbroadStudentActivityCreate,
    current_user=Depends(dependencies.get_current_user),
    db:       Session = Depends(dependencies.get_db),
):
    # if in_data.activity_type.name != "ABROAD":
    #     raise HTTPException(400, "activity_type must be ABROAD")

    logger.info(f"{current_user.username} creating ABROAD activity for student {stu_id}: {in_data}")

    try:
        new_act = crud.create_abroad_student_activity(db, stu_id, in_data)
        return new_act
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.get("/phd-students/{stu_id}/activities/{stu_act_id}", response_model=schemas.StudentActivityRead)
def read_student_activity(
    stu_id:  int,
    stu_act_id:  int,
    current_user=Depends(dependencies.get_current_user),
    db:      Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} fetching student activity #{stu_act_id} for student #{stu_id}")
    try:
        sa = crud.get_student_activity(db, stu_act_id)
        if not sa or sa.phd_student_id != stu_id:
            raise StudentActivityNotFound(f"Student activity #{stu_act_id} for student {stu_id} not found")
        return sa
    except StudentActivityNotFound as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.put("/phd-students/{stu_id}/activities/{stu_act_id}/grad", response_model=schemas.StudentActivityRead)
def update_student_grad_school_activity(
    stu_id:  int,
    stu_act_id:  int,
    in_data: schemas.GradSchoolStudentActivityCreate,
    current_user=Depends(dependencies.get_current_user),
    db:      Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating student grad school activity #{stu_act_id} "
                f"for student #{stu_id} → {in_data}")
    try:
        updated = crud.update_student_activity(db, stu_act_id, stu_id, in_data)
        return updated
    except StudentActivityNotFound as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/phd-students/{stu_id}/activities/{stu_act_id}/abroad", response_model=schemas.StudentActivityRead)
def update_student_abroad_activity(
    stu_id:  int,
    stu_act_id:  int,
    in_data: schemas.AbroadStudentActivityCreate,
    current_user=Depends(dependencies.get_current_user),
    db:      Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating student abroad activity #{stu_act_id} "
                f"for student #{stu_id} → {in_data}")
    try:
        updated = crud.update_student_activity(db, stu_act_id, stu_id, in_data)
        return updated
    except StudentActivityNotFound as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/phd-students/{stu_id}/activities/{stu_act_id}", status_code=204)
def delete_student_activity(
    stu_id: int,
    stu_act_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting student activity #{stu_act_id} for student #{stu_id}")
    try:
        crud.delete_student_activity(db, stu_act_id, stu_id)
    except StudentActivityNotFound as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="PhD Student-related courses endpoints">
# — Courses —

@router.get("/phd-students/{stu_id}/courses/", response_model=List[schemas.CourseStudentRead])
def list_student_courses(
    stu_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing courses for phd student {stu_id}")
    return crud.get_student_courses(db, stu_id)


# </editor-fold>
