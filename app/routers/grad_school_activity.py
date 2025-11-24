import logging
from fastapi import (
    APIRouter, Depends, HTTPException,
    Response, Query
)
from fastapi.responses import StreamingResponse
from typing import List, Optional

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
from ..excel_utils import generate_excel_response

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

# <editor-fold desc="GradSchoolActivity-related student activities endpoints">
# --- GradSchoolActivity-related student activities endpoints ---

@router.get(
    "/grad-school-activities/{gsa_id}/student-activities/",
    response_model=List[schemas.StudentActivityRead]
)
def list_student_activities_for_grad_school_activity(
    gsa_id: int,
    search: Optional[str] = Query(
        None, description="Substring search on student first or last name"
    ),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    # Verify the grad school activity exists
    from ..crud import get_grad_school_activity
    if not get_grad_school_activity(db, gsa_id):
        logger.warning(f"GradSchoolActivity #{gsa_id} not found")
        raise HTTPException(404, f"GradSchoolActivity #{gsa_id} not found")

    logger.info(
        f"{current_user.username} listing student activities for "
        f"grad_school_activity #{gsa_id}"
        f"{' with search=' + search if search else ''}"
    )

    return crud.list_student_activities_for_grad_school(db, grad_school_activity_id=gsa_id, search=search)


@router.get("/grad-school-activities/{gsa_id}/student-activities/export/emails")
def export_gsa_student_emails(
    gsa_id: int,
    search: Optional[str] = Query(None),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    """
    Generate a JSON list of emails for students in a specific Grad School Activity.
    """
    logger.info(f"{current_user.username} fetching emails for GSA #{gsa_id}")

    # 1. Retrieve data
    # Note: We reuse the existing CRUD logic which handles the search filter
    activities = crud.list_student_activities_for_grad_school(
        db, grad_school_activity_id=gsa_id, search=search
    )

    # 2. Build filter summary
    filter_info = []
    if search:
        filter_info.append(f"Search: {search}")
    else:
        filter_info.append("All students in activity")

    # 3. Extract emails
    # Hierarchy: StudentActivity -> PhdStudent (student) -> PersonRole -> Person -> email
    emails = []
    for act in activities:
        # Check relationships exist to avoid errors
        if act.student and act.student.person_role.person.email:
            emails.append(act.student.person_role.person.email)

    # 4. Return JSON
    return {
        "count": len(emails),
        "filter_summary": filter_info,
        "emails": emails
    }


# </editor-fold>

# <editor-fold desc="GradSchoolActivity-related courses endpoints">
# --- GradSchoolActivity-related courses endpoints ---

@router.get("/grad-school-activities/{gsa_id}/courses/",
            response_model=List[schemas.CourseRead])
def list_courses_for_grad_school_activity(
        gsa_id: int,
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)):
    # Verify the grad school activity exists (reuse get_grad_school_activity)
    from ..crud import get_grad_school_activity
    if not get_grad_school_activity(db, gsa_id):
        logger.warning(f"GradSchoolActivity #{gsa_id} not found")
        raise HTTPException(404, f"GradSchoolActivity #{gsa_id} not found")

    logger.info(f"{current_user.username} listing courses for grad_school_activity #{gsa_id}")
    results = crud.list_courses(db, activity_id=gsa_id)
    return results


# </editor-fold>

# <editor-fold desc="GradSchoolActivity Export endpoints">

@router.get("/grad-school-activities/export/grad-school-activities.xlsx")
def export_grad_school_activities_to_excel(
    activity_type_id:   Optional[int] = Query(None, ge=1),
    description:        Optional[str] = Query(None),
    year:               Optional[int] = Query(None),
    search:             Optional[str] = Query(None),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    """
    Export a list of grad school activities to an Excel file, applying the same
    filters as the main list view.
    """
    logger.info(f"{current_user.username} exporting grad school activities")

    # Reuse the same CRUD function to get the filtered data
    activities = crud.list_grad_school_activities(
        db,
        activity_type_id=activity_type_id,
        description=description,
        year=year,
        search=search
    )

    # --- 1. BUILD THE FILTER INFO LIST ---
    filter_info = []
    if search:
        filter_info.append(f"Search: {search}")
    if year:
        filter_info.append(f"Year: {year}")
    if activity_type_id:
        # Fetch the activity type name for a more descriptive filter line
        activity_type = crud.get_grad_school_activity_type(db, activity_type_id)
        if activity_type:
            filter_info.append(f"Activity Type: {activity_type.type}")

    # Prepare the data in the desired format
    data_to_export = [
        {
            "Activity Type": act.activity_type.type,
            "Year": act.year,
            "Description": act.description
        } for act in activities
    ]
    headers = ["Activity Type", "Year", "Description"]

    # --- 2. PASS THE FILTERS TO THE GENERATOR ---
    excel_buffer = generate_excel_response(
        data_to_export,
        headers,
        "Grad School Activities",
        filter_info=filter_info  # Pass the list here
    )

    # Return the file as a downloadable response
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=grad_school_activities.xlsx"
        }
    )


# </editor-fold>
