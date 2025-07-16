import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError

router = APIRouter(tags=["postdocs"])
logger = logging.getLogger(__name__)


# <editor-fold desc="Postdoc endpoints">
# --- Postdoc endpoints ---

@router.get("/postdocs/{pd_id}", response_model=schemas.PostdocRead)
def read_postdoc(
    pd_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    p = crud.get_postdoc(db, pd_id)
    if not p:
        logger.warning(f"Postdoc #{pd_id} not found")
        raise HTTPException(404, f"Postdoc #{pd_id} not found")
    logger.info(f"{current_user.username} fetched postdoc #{pd_id}")
    return p


@router.get("/postdocs/", response_model=List[schemas.PostdocRead])
def list_postdocs(
    person_role_id: Optional[int] = Query(None, ge=1, description="Filter by person_role_id"),
    is_active:      Optional[bool] = Query(None, description="Only active/inactive roles"),
    cohort_number:  Optional[int] = Query(None, ge=0, description="Filter by cohort number"),
    is_outgoing:    Optional[bool] = Query(None, description="Only incoming/outgoing postdocs"),
    institution_id: Optional[int] = Query(None, ge=1, description="Filter by institution"),
    field_id:       Optional[int] = Query(None, ge=1, description="Filter by academic field"),
    branch_id:      Optional[int] = Query(None, ge=1, description="Filter by academic branch"),
    search:         Optional[str] = Query(None, description="Substring search on person name"),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(
        f"{current_user.username} listed postdocs "
        f"(person_role_id={person_role_id}, is_active={is_active}, cohort={cohort_number}, "
        f"institution_id={institution_id}, field_id={field_id}, branch_id={branch_id}, search={search!r})"
    )
    return crud.list_postdocs(
        db,
        person_role_id=person_role_id,
        is_active=is_active,
        cohort_number=cohort_number,
        is_outgoing=is_outgoing,
        institution_id=institution_id,
        field_id=field_id,
        branch_id=branch_id,
        search=search,
    )


@router.post("/postdocs/", response_model=schemas.PostdocRead)
def create_postdoc(
    p_in: schemas.PostdocCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating postdoc {p_in}")
    try:
        return crud.create_postdoc(db, p_in)
    except Exception as e:
        logger.warning(f"Failed to create postdoc: {e}")
        raise HTTPException(400, str(e))


@router.put("/postdocs/{pd_id}", response_model=schemas.PostdocRead)
def update_postdoc(
    pd_id: int,
    p_in: schemas.PostdocUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating postdoc #{pd_id} → {p_in}")
    try:
        return crud.update_postdoc(db, pd_id, p_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/postdocs/{pd_id}", status_code=204)
def delete_postdoc(
    pd_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting postdoc #{pd_id}")
    try:
        crud.delete_postdoc(db, pd_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>
