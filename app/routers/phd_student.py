import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError

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
    person_role_id: Optional[int] = Query(None, ge=1),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} listed phd_students (person_role_id={person_role_id})")
    return crud.list_phd_students(db, person_role_id=person_role_id)


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
