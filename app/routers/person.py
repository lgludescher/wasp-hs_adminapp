import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError

router = APIRouter(tags=["people"])
logger = logging.getLogger(__name__)


# <editor-fold desc="Person endpoints">
# --- Person endpoints ---

@router.get("/people/{person_id}", response_model=schemas.PersonRead)
def read_person(
    person_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    p = crud.get_person(db, person_id)
    if not p:
        logger.warning(f"Person #{person_id} not found")
        raise HTTPException(404, f"Person #{person_id} not found")
    logger.info(f"{current_user.username} fetched person #{person_id}")
    return p


@router.get("/people/", response_model=List[schemas.PersonRead])
def list_people(
    search: Optional[str] = Query(None, description="Substring search on first/last name or email"),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} listed people (search={search!r})")
    return crud.list_persons(db, search=search)


@router.post("/people/", response_model=schemas.PersonRead)
def create_person(
    person_in: schemas.PersonCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating person {person_in.first_name} {person_in.last_name}")
    try:
        return crud.create_person(db, person_in)
    except Exception as e:
        logger.warning(f"Failed to create person: {e}")
        raise HTTPException(400, str(e))


@router.put("/people/{person_id}", response_model=schemas.PersonRead)
def update_person(
    person_id: int,
    person_in: schemas.PersonUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating person #{person_id} → {person_in}")
    try:
        return crud.update_person(db, person_id, person_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/people/{person_id}", status_code=204)
def delete_person(
    person_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting person #{person_id}")
    try:
        crud.delete_person(db, person_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="PersonRole endpoints">
# --- PersonRole endpoints ---

@router.get("/person-roles/{person_role_id}", response_model=schemas.PersonRoleReadFull)
def read_person_role(
    person_role_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    pr = crud.get_person_role(db, person_role_id)
    if not pr:
        logger.warning(f"PersonRole #{person_role_id} not found")
        raise HTTPException(404, f"PersonRole #{person_role_id} not found")
    logger.info(f"{current_user.username} fetched person_role #{person_role_id}")
    return pr


@router.get("/person-roles/", response_model=List[schemas.PersonRoleReadFull])
def list_person_roles(
    person_id: Optional[int] = Query(None, ge=1),
    role_id:   Optional[int] = Query(None, ge=1),
    active:    Optional[bool] = Query(None),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} listed person_roles (person_id={person_id}, role_id={role_id}, active={active})")
    return crud.list_person_roles(db, person_id=person_id, role_id=role_id, active=active)


@router.post("/person-roles/", response_model=schemas.PersonRoleReadFull)
def create_person_role(
    pr_in: schemas.PersonRoleCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating person_role {pr_in}")
    try:
        return crud.create_person_role(db, pr_in)
    except Exception as e:
        logger.warning(f"Failed to create person_role: {e}")
        raise HTTPException(400, str(e))


@router.put("/person-roles/{person_role_id}", response_model=schemas.PersonRoleReadFull)
def update_person_role(
    person_role_id: int,
    pr_in: schemas.PersonRoleUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating person_role #{person_role_id} → {pr_in}")
    try:
        return crud.update_person_role(db, person_role_id, pr_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/person-roles/{person_role_id}", status_code=204)
def delete_person_role(
    person_role_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting person_role #{person_role_id}")
    try:
        crud.delete_person_role(db, person_role_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>
