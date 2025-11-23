import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
from ..excel_utils import generate_excel_response

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
    is_incoming:    Optional[bool] = Query(None, description="Only incoming/outgoing postdocs"),
    is_graduated:   Optional[bool] = Query(None, description="Filter by is_graduated"),
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
        f"is_incoming={is_incoming}, is_graduated={is_graduated}, "
        f"institution_id={institution_id}, field_id={field_id}, branch_id={branch_id}, search={search!r})"
    )
    return crud.list_postdocs(
        db,
        person_role_id=person_role_id,
        is_active=is_active,
        cohort_number=cohort_number,
        is_incoming=is_incoming,
        is_graduated=is_graduated,
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

# <editor-fold desc="Postdoc Export endpoints">

@router.get("/postdocs/export/postdocs.xlsx")
def export_postdocs_to_excel(
    view_mode:      str = Query("default", description="The view mode ('default' or 'activity')"),
    person_role_id: Optional[int] = Query(None, ge=1),
    is_active:      Optional[bool] = Query(None),
    cohort_number:  Optional[int] = Query(None, ge=0),
    is_incoming:    Optional[bool] = Query(None),
    is_graduated:   Optional[bool] = Query(None),
    institution_id: Optional[int] = Query(None, ge=1),
    field_id:       Optional[int] = Query(None, ge=1),
    branch_id:      Optional[int] = Query(None, ge=1),
    search:         Optional[str] = Query(None),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    """
    Export a list of postdocs to an Excel file, applying the same
    filters as the main list view and respecting the view mode.
    """
    logger.info(f"{current_user.username} exporting postdocs (view_mode={view_mode})")

    # 1. Reuse the exact same CRUD function to get the filtered data
    postdocs = crud.list_postdocs(
        db, person_role_id=person_role_id, is_active=is_active, cohort_number=cohort_number,
        is_incoming=is_incoming, is_graduated=is_graduated, institution_id=institution_id,
        field_id=field_id, branch_id=branch_id, search=search,
    )

    # --- 2. BUILD THE FILTER INFO LIST ---
    filter_info = []
    if view_mode == "activity":
        filter_info.append(f"View Mode: Current Position")
    else:  # view_mode == default
        filter_info.append(f"View Mode: {view_mode.title()}")
    # filter_info = [f"View Mode: {view_mode.title()}"]
    if search:
        filter_info.append(f"Search: {search}")
    if is_active is not None:
        status = "Active" if is_active else "Inactive"
        filter_info.append(f"Status: {status}")
    if cohort_number is not None:
        filter_info.append(f"Cohort: {cohort_number}")
    if is_incoming is not None:
        mobility = "Incoming" if is_incoming else "Outgoing"
        filter_info.append(f"Mobility Status: {mobility}")
    if is_graduated is not None:
        filter_info.append(f"Graduated: {'Yes' if is_graduated else 'No'}")
    if institution_id:
        institution = crud.get_institution(db, institution_id)
        if institution:
            filter_info.append(f"Institution: {institution.institution}")
    if branch_id:
        branch = crud.get_branch(db, branch_id)
        if branch:
            filter_info.append(f"Branch: {branch.branch}")
    if field_id:
        field = crud.get_field(db, field_id)
        if field:
            filter_info.append(f"Field: {field.field}")

    # 3. Prepare headers and data based on the view mode
    headers = []
    data_to_export = []

    if view_mode == 'activity':
        headers = ["Name", "Cohort", "Graduated", "Current Title", "Current Institution"]
        for p in postdocs:
            title = p.current_title.title if p.current_title else p.current_title_other
            institution = p.current_institution.institution if p.current_institution else p.current_institution_other
            data_to_export.append({
                "Name": f"{p.person_role.person.first_name} {p.person_role.person.last_name}",
                "Cohort": p.cohort_number,
                "Graduated": "Yes" if p.is_graduated else "No",
                "Current Title": title,
                "Current Institution": institution
            })
    else:  # Default view
        headers = ["Name", "Email", "Cohort", "Mobility Status", "Graduated", "Start Date", "End Date"]
        for p in postdocs:
            data_to_export.append({
                "Name": f"{p.person_role.person.first_name} {p.person_role.person.last_name}",
                "Email": p.person_role.person.email,
                "Cohort": p.cohort_number,
                "Mobility Status": "Incoming" if p.is_incoming else "Outgoing",
                "Graduated": "Yes" if p.is_graduated else "No",
                "Start Date": p.person_role.start_date.strftime("%Y-%m-%d") if p.person_role.start_date else "",
                "End Date": p.person_role.end_date.strftime("%Y-%m-%d") if p.person_role.end_date else ""
            })

    # --- 4. PASS THE FILTERS TO THE GENERATOR ---
    excel_buffer = generate_excel_response(
        data_to_export,
        headers,
        "Postdocs",
        filter_info=filter_info  # Pass the list here
    )

    # 5. Return the file as a downloadable response
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=postdocs.xlsx"}
    )


@router.get("/postdocs/export/emails")
def export_postdoc_emails(
    person_role_id: Optional[int] = Query(None, ge=1),
    is_active:      Optional[bool] = Query(None),
    cohort_number:  Optional[int] = Query(None, ge=0),
    is_incoming:    Optional[bool] = Query(None),
    is_graduated:   Optional[bool] = Query(None),
    institution_id: Optional[int] = Query(None, ge=1),
    field_id:       Optional[int] = Query(None, ge=1),
    branch_id:      Optional[int] = Query(None, ge=1),
    search:         Optional[str] = Query(None),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    """
    Generate a JSON list of emails and filter metadata for Postdocs.
    """
    logger.info(f"{current_user.username} fetching Postdoc emails")

    # 1. Retrieve data
    postdocs = crud.list_postdocs(
        db, person_role_id=person_role_id, is_active=is_active, cohort_number=cohort_number,
        is_incoming=is_incoming, is_graduated=is_graduated, institution_id=institution_id,
        field_id=field_id, branch_id=branch_id, search=search,
    )

    # 2. Build filter summary
    filter_info = []
    if search:
        filter_info.append(f"Search: {search}")
    if is_active is not None:
        status = "Active" if is_active else "Inactive"
        filter_info.append(f"Status: {status}")
    if cohort_number is not None:
        filter_info.append(f"Cohort: {cohort_number}")
    if is_incoming is not None:
        mobility = "Incoming" if is_incoming else "Outgoing"
        filter_info.append(f"Mobility Status: {mobility}")
    if is_graduated is not None:
        filter_info.append(f"Graduated: {'Yes' if is_graduated else 'No'}")
    if institution_id:
        institution = crud.get_institution(db, institution_id)
        if institution:
            filter_info.append(f"Institution: {institution.institution}")
    if branch_id:
        branch = crud.get_branch(db, branch_id)
        if branch:
            filter_info.append(f"Branch: {branch.branch}")
    if field_id:
        field = crud.get_field(db, field_id)
        if field:
            filter_info.append(f"Field: {field.field}")

    # 3. Extract emails
    emails = [
        p.person_role.person.email
        for p in postdocs
        if p.person_role.person.email
    ]

    # 4. Return JSON
    return {
        "count": len(emails),
        "filter_summary": filter_info,
        "emails": emails
    }


# </editor-fold>
