import logging
from fastapi import (
    APIRouter, Depends, HTTPException,
    Response, Query
)
from typing import List, Optional

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError

router = APIRouter(tags=["grad_school_activities"])
logger = logging.getLogger(__name__)


# <editor-fold desc="GradSchoolActivityType endpoints">
# --- Grad School Activity Type endpoints ---

@router.get("/grad-school-activity-types/{gsat_id}", response_model=schemas.GradSchoolActivityTypeRead)
def read_grad_school_activity_type(
    gsat_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    gsat = crud.get_grad_school_activity_type(db, gsat_id)
    if not gsat:
        logger.warning(f"Grad School Activity Type #{gsat_id} not found")
        raise HTTPException(404, f"Grad School Activity Type #{gsat_id} not found")

    logger.info(f"{current_user.username} fetched grad school activity type '{gsat.type}'")

    return gsat


@router.get("/grad-school-activity-types/", response_model=List[schemas.GradSchoolActivityTypeRead])
def list_grad_school_activity_types(
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} listed grad school activity types")
    return crud.list_grad_school_activity_types(db)


@router.post("/grad-school-activity-types/", response_model=schemas.GradSchoolActivityTypeRead)
def create_grad_school_activity_type(
    gsat_in: schemas.GradSchoolActivityTypeCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} creating grad school activity type {gsat_in.type}")

    return crud.create_grad_school_activity_type(db, gsat_in)


@router.put("/grad-school-activity-types/{gsat_id}", response_model=schemas.GradSchoolActivityTypeRead)
def update_grad_school_activity_type(
    gsat_id: int,
    gsat_in: schemas.GradSchoolActivityTypeUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating grad school activity type {gsat_id} → {gsat_in}")

    try:
        return crud.update_grad_school_activity_type(db, gsat_id, gsat_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/grad-school-activity-types/{gsat_id}", status_code=204)
def delete_grad_school_activity_type(
    gsat_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} deleting grad school activity type {gsat_id}")

    try:
        crud.delete_grad_school_activity_type(db, gsat_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="GradSchoolActivity endpoints">
# --- Grad School Activity endpoints ---

@router.get("/grad-school-activities/{gsa_id}", response_model=schemas.GradSchoolActivityRead)
def read_grad_school_activity(
    gsa_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    gsa = crud.get_grad_school_activity(db, gsa_id)
    if not gsa:
        logger.warning(f"Grad school activity #{gsa_id} not found")
        raise HTTPException(404, f"Grad school activity #{gsa_id} not found")

    logger.info(f"{current_user.username} fetched grad school activity [{gsa.id}]")

    return gsa


@router.get("/grad-school-activities/", response_model=List[schemas.GradSchoolActivityRead])
def list_grad_school_activities(
    activity_type_id:   Optional[int] = Query(None, ge=1),
    description:        Optional[str] = Query(None),
    year:               Optional[int] = Query(None),
    search:             Optional[str] = Query(None),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed grad school activities (activity_type_id={activity_type_id},"
                f"description={description}, year={year}, search={search!r})")
    return crud.list_grad_school_activities(
        db,
        activity_type_id=activity_type_id,
        description=description,
        year=year,
        search=search
    )


@router.post("/grad-school-activities/", response_model=schemas.GradSchoolActivityRead)
def create_grad_school_activity(
    gsa_in: schemas.GradSchoolActivityCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} creating grad school activity {gsa_in}")
    try:
        return crud.create_grad_school_activity(db, gsa_in)
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/grad-school-activities/{gsa_id}", response_model=schemas.GradSchoolActivityRead)
def update_grad_school_activity(
    gsa_id: int,
    gsa_in: schemas.GradSchoolActivityUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating grad school activity {gsa_id} → {gsa_in}")

    try:
        return crud.update_grad_school_activity(db, gsa_id, gsa_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/grad-school-activities/{gsa_id}", status_code=204)
def delete_grad_school_activity(
    gsa_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} deleting grad school activity {gsa_id}")

    try:
        crud.delete_grad_school_activity(db, gsa_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>
