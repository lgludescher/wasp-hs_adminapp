import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
from ..excel_utils import generate_excel_response

router = APIRouter(prefix="/institutions", tags=["institutions"])

logger = logging.getLogger(__name__)


# <editor-fold desc="Institution endpoints">

@router.get("/{institution_id}", response_model=schemas.InstitutionRead)
def read_institution(
    institution_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    inst = crud.get_institution(db, institution_id)
    if not inst:
        logger.warning(f"Institution #{institution_id} not found")
        raise HTTPException(404, f"Institution #{institution_id} not found")

    logger.info(f"{current_user.username} fetched institution '{inst.institution}'")

    return inst


@router.get("/", response_model=List[schemas.InstitutionRead])
def list_institutions(
    search: Optional[str] = Query(None, description="Substring search on name"),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} listed institutions (search={search!r})")
    return crud.get_institutions(db, search=search)


@router.post("/", response_model=schemas.InstitutionRead)
def create_institution(
    inst_in: schemas.InstitutionCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} creating institution {inst_in.institution}")

    # Check for existing institution
    existing = crud.get_institutions(db, name=inst_in.institution)
    if existing:
        logger.warning(f"Attempt to create duplicate institution {inst_in.institution} by {current_user.username}")
        raise HTTPException(status_code=400, detail=f"Institution '{inst_in.institution}' already exists")

    return crud.create_institution(db, inst_in)


@router.put("/{institution_id}", response_model=schemas.InstitutionRead)
def update_institution(
    institution_id: int,
    inst_in: schemas.InstitutionUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating institution {institution_id} → {inst_in}")

    try:
        return crud.update_institution(db, institution_id, inst_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/{institution_id}", status_code=204)
def delete_institution(
    institution_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} deleting institution {institution_id}")

    try:
        crud.delete_institution(db, institution_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Institution Export endpoints">

@router.get("/export/institutions.xlsx")
def export_institutions_to_excel(
    search: Optional[str] = Query(None, description="Substring search on name"),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    """
    Export a list of institutions to an Excel file, applying the same
    search filter as the main list view.
    """
    logger.info(f"{current_user.username} exporting institutions (search={search!r})")

    # Reuse the same CRUD function to get the filtered data
    institutions = crud.get_institutions(db, search=search)

    # Prepare the data in the desired format (list of dicts)
    data_to_export = [
        {"Institution Name": inst.institution} for inst in institutions
    ]
    headers = ["Institution Name"]

    # Generate the Excel file in memory
    excel_buffer = generate_excel_response(data_to_export, headers, "Institutions")

    # Return the file as a downloadable response
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=institutions.xlsx"
        }
    )


# </editor-fold>
