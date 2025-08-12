import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
from ..excel_utils import generate_excel_response

router = APIRouter(tags=["researchers"])
logger = logging.getLogger(__name__)


# <editor-fold desc="ResearcherTitle endpoints">
# --- ResearcherTitle endpoints ---

@router.get("/researcher-titles/{rt_id}", response_model=schemas.ResearcherTitleRead)
def read_researcher_title(
    rt_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    rt = crud.get_researcher_title(db, rt_id)
    if not rt:
        logger.warning(f"ResearcherTitle #{rt_id} not found")
        raise HTTPException(404, f"ResearcherTitle #{rt_id} not found")
    logger.info(f"{current_user.username} fetched researcher_title #{rt_id}")
    return rt


@router.get("/researcher-titles/", response_model=List[schemas.ResearcherTitleRead])
def list_researcher_titles(
    search: Optional[str] = Query(None, description="Substring search on title"),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} listed researcher titles")
    return crud.list_researcher_titles(db, search=search)


@router.post("/researcher-titles/", response_model=schemas.ResearcherTitleRead)
def create_researcher_title(
    rt_in: schemas.ResearcherTitleCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating researcher_title {rt_in.title}")
    try:
        return crud.create_researcher_title(db, rt_in)
    except Exception as e:
        logger.warning(f"Failed to create researcher_title: {e}")
        raise HTTPException(400, str(e))


@router.put("/researcher-titles/{rt_id}", response_model=schemas.ResearcherTitleRead)
def update_researcher_title(
    rt_id: int,
    rt_in: schemas.ResearcherTitleUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating researcher_title #{rt_id} → {rt_in}")
    try:
        return crud.update_researcher_title(db, rt_id, rt_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/researcher-titles/{rt_id}", status_code=204)
def delete_researcher_title(
    rt_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting researcher_title #{rt_id}")
    try:
        crud.delete_researcher_title(db, rt_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Researcher endpoints">
# --- Researcher endpoints ---

@router.get("/researchers/{res_id}", response_model=schemas.ResearcherRead)
def read_researcher(
    res_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    r = crud.get_researcher(db, res_id)
    if not r:
        logger.warning(f"Researcher #{res_id} not found")
        raise HTTPException(404, f"Researcher #{res_id} not found")
    logger.info(f"{current_user.username} fetched researcher #{res_id}")
    return r


@router.get("/researchers/", response_model=List[schemas.ResearcherRead])
def list_researchers(
    person_role_id:   Optional[int] = Query(None, ge=1, description="Filter by person_role_id"),
    is_active:        Optional[bool] = Query(None, description="Only active/inactive roles"),
    title_id:         Optional[int] = Query(None, ge=1, description="Filter by researcher title"),
    institution_id:   Optional[int] = Query(None, ge=1, description="Filter by institution"),
    field_id:         Optional[int] = Query(None, ge=1, description="Filter by academic field"),
    branch_id:        Optional[int] = Query(None, ge=1, description="Filter by academic branch"),
    search:           Optional[str] = Query(None, description="Substring search on person name"),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(
        f"{current_user.username} listed researchers "
        f"(person_role_id={person_role_id}, is_active={is_active}, title_id={title_id}, "
        f"institution_id={institution_id}, field_id={field_id}, branch_id={branch_id}, search={search!r})"
    )
    return crud.list_researchers(
        db,
        person_role_id=person_role_id,
        is_active=is_active,
        title_id=title_id,
        institution_id=institution_id,
        field_id=field_id,
        branch_id=branch_id,
        search=search,
    )


@router.post("/researchers/", response_model=schemas.ResearcherRead)
def create_researcher(
    r_in: schemas.ResearcherCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating researcher {r_in}")
    try:
        return crud.create_researcher(db, r_in)
    except Exception as e:
        logger.warning(f"Failed to create researcher: {e}")
        raise HTTPException(400, str(e))


@router.put("/researchers/{res_id}", response_model=schemas.ResearcherRead)
def update_researcher(
    res_id: int,
    r_in: schemas.ResearcherUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating researcher #{res_id} → {r_in}")
    try:
        return crud.update_researcher(db, res_id, r_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/researchers/{res_id}", status_code=204)
def delete_researcher(
    res_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting researcher #{res_id}")
    try:
        crud.delete_researcher(db, res_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Researcher Export endpoints">

@router.get("/researchers/export/researchers.xlsx")
def export_researchers_to_excel(
    person_role_id:   Optional[int] = Query(None, ge=1),
    is_active:        Optional[bool] = Query(None),
    title_id:         Optional[int] = Query(None, ge=1),
    institution_id:   Optional[int] = Query(None, ge=1),
    field_id:         Optional[int] = Query(None, ge=1),
    branch_id:        Optional[int] = Query(None, ge=1),
    search:           Optional[str] = Query(None),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    """
    Export a list of researchers to an Excel file, applying the same
    filters as the main list view.
    """
    logger.info(f"{current_user.username} exporting researchers")

    # 1. Reuse the exact same CRUD function to get the filtered data
    researchers = crud.list_researchers(
        db,
        person_role_id=person_role_id,
        is_active=is_active,
        title_id=title_id,
        institution_id=institution_id,
        field_id=field_id,
        branch_id=branch_id,
        search=search,
    )

    # 2. Prepare the data in the desired format
    data_to_export = [
        {
            "Title": r.title.title if r.title else "",
            "Name": f"{r.person_role.person.first_name} {r.person_role.person.last_name}",
            "Email": r.person_role.person.email,
            "Start Date": r.person_role.start_date.strftime("%Y-%m-%d") if r.person_role.start_date else "",
            "End Date": r.person_role.end_date.strftime("%Y-%m-%d") if r.person_role.end_date else ""
        } for r in researchers
    ]
    headers = ["Title", "Name", "Email", "Start Date", "End Date"]

    # 3. Generate the Excel file in memory
    excel_buffer = generate_excel_response(data_to_export, headers, "Researchers")

    # 4. Return the file as a downloadable response
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=researchers.xlsx"
        }
    )


# </editor-fold>
