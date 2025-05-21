import logging
from fastapi import (
    APIRouter, Depends, HTTPException,
    Response, Query
)
from typing import List, Optional
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError

router = APIRouter(tags=["domains"])

logger = logging.getLogger(__name__)


# <editor-fold desc="Branch endpoints">
# --- Branch endpoints ---

@router.get("/branches/{branch_id}", response_model=schemas.BranchRead)
def read_branch(
    branch_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    branch = crud.get_branch(db, branch_id)
    if not branch:
        logger.warning(f"Branch #{branch_id} not found")
        raise HTTPException(404, f"Branch #{branch_id} not found")

    logger.info(f"{current_user.username} fetched branch '{branch.branch}'")

    return branch


@router.get("/branches/", response_model=List[schemas.BranchRead])
def list_branches(
    search: Optional[str] = Query(None, description="Substring search"),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} listed branches (search={search!r})")
    return crud.get_branches(db, search=search)


@router.post("/branches/", response_model=schemas.BranchRead)
def create_branch(
    branch_in: schemas.BranchCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} creating branch {branch_in.branch}")

    existing = crud.get_branches(db, name=branch_in.branch)
    if existing:
        logger.warning(f"Attempt to create duplicate branch {branch_in.branch} by {current_user.username}")
        raise HTTPException(400, f"Branch '{branch_in.branch}' already exists")
    return crud.create_branch(db, branch_in)


@router.put("/branches/{branch_id}", response_model=schemas.BranchRead)
def update_branch(
    branch_id: int,
    branch_in: schemas.BranchUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating institution {branch_id} → {branch_in}")

    try:
        return crud.update_branch(db, branch_id, branch_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/branches/{branch_id}", status_code=204)
def delete_branch(
    branch_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} deleting branch {branch_id}")

    try:
        crud.delete_branch(db, branch_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Field endpoints">
# --- Field endpoints ---

@router.get("/fields/{field_id}", response_model=schemas.FieldRead)
def read_field(
    field_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    field = crud.get_field(db, field_id)
    if not field:
        logger.warning(f"Field #{field_id} not found")
        raise HTTPException(404, f"Field #{field_id} not found")

    logger.info(f"{current_user.username} fetched field '{field.field} in branch {field.branch_id}'")

    return field


@router.get("/fields/", response_model=List[schemas.FieldRead])
def list_fields(
    branch_id: Optional[int] = Query(None, ge=1, description="Filter by branch ID"),
    search:    Optional[str] = Query(None, description="Substring search"),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} listed fields (search={search!r}) in branch {branch_id}")
    return crud.get_fields(db, branch_id=branch_id, search=search)


@router.post("/fields/", response_model=schemas.FieldRead)
def create_field(
    field_in: schemas.FieldCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} creating field {field_in.field} in branch {field_in.branch_id}")

    existing = crud.get_fields(db, branch_id=field_in.branch_id, name=field_in.field)
    if existing:
        logger.warning(f"Attempt to create duplicate field {field_in.field} in "
                       f"branch {field_in.branch_id} by {current_user.username}")
        raise HTTPException(
            400,
            f"Field '{field_in.field}' already exists in branch {field_in.branch_id}"
        )

    return crud.create_field(db, field_in)


@router.put("/fields/{field_id}", response_model=schemas.FieldRead)
def update_field(
    field_id: int,
    field_in: schemas.FieldUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating field {field_id} → {field_in}")

    try:
        return crud.update_field(db, field_id, field_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/fields/{field_id}", status_code=204)
def delete_field(
    field_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} deleting field {field_id}")

    try:
        crud.delete_field(db, field_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>
