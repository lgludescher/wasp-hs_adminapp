import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies, models
from ..crud import EntityNotFoundError
from ..models import EntityType
from ..excel_utils import generate_excel_response

router = APIRouter(tags=["reports"])
logger = logging.getLogger(__name__)


# <editor-fold desc="Report supervisions endpoints">
# --- Supervisions ---

@router.get(
    "/reports/supervisions/",
    response_model=List[schemas.SupervisionRead],
    summary="Search and Filter Supervisions for Reports"
)
def get_supervisions_report(
        # Filters
        is_main: Optional[bool] = Query(None, description="Filter by main supervision status"),
        is_active_supervisor: Optional[bool] = Query(None, description="Filter active/inactive supervisors"),
        is_active_student: Optional[bool] = Query(None, description="Filter active/inactive students"),
        supervisor_role_id: Optional[int] = Query(None, description="Filter by specific supervisor role ID"),
        supervisee_role_id: Optional[int] = Query(None, description="Filter by specific student role ID"),
        cohort_number: Optional[int] = Query(None, description="Filter by student/postdoc cohort number"),
        search_supervisor: Optional[str] = Query(None, description="Search by supervisor's first or last name"),

        # Dependencies
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),  # Assuming you need auth
):
    """
    Generates a list of supervisions based on various filters.
    Useful for generating reports.
    Returns a list of supervision links (Supervisor <-> Student).
    """
    logger.info(f"{current_user.username} accessing supervision report")

    return crud.report_supervisions(
        db,
        is_main=is_main,
        is_active_supervisor=is_active_supervisor,
        is_active_student=is_active_student,
        supervisor_role_id=supervisor_role_id,
        supervisee_role_id=supervisee_role_id,
        cohort_number=cohort_number,
        search_supervisor=search_supervisor
    )


@router.get("/reports/supervisions/export/excel")
def export_supervisors_to_excel(
        is_main: Optional[bool] = Query(None),
        is_active_supervisor: Optional[bool] = Query(None),
        is_active_student: Optional[bool] = Query(None),
        supervisor_role_id: Optional[int] = Query(None),
        supervisee_role_id: Optional[int] = Query(None),
        cohort_number: Optional[int] = Query(None),
        search_supervisor: Optional[str] = Query(None),

        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),
):
    """
    Export the Supervisors Report to Excel.
    Aggregates supervision links into unique supervisors.
    """
    logger.info(f"{current_user.username} exporting supervisors report to Excel")

    # 1. Fetch Raw Data (Links)
    links = crud.report_supervisions(
        db,
        is_main=is_main,
        is_active_supervisor=is_active_supervisor,
        is_active_student=is_active_student,
        supervisor_role_id=supervisor_role_id,
        supervisee_role_id=supervisee_role_id,
        cohort_number=cohort_number,
        search_supervisor=search_supervisor
    )

    # 2. Aggregate Logic (Links -> Unique Supervisors)
    # Map: supervisor_role_id -> { 'person_role': obj, 'is_main': bool }
    unique_map = {}
    for link in links:
        sup_id = link.supervisor_role_id
        if sup_id not in unique_map:
            unique_map[sup_id] = {
                "person_role": link.supervisor,
                "is_main": link.is_main
            }
        else:
            # Apply OR logic: if they are main in ANY link, they are main in the report
            unique_map[sup_id]["is_main"] = unique_map[sup_id]["is_main"] or link.is_main

    # Sort aggregated list by name (optional, but good for UX)
    aggregated_list = sorted(
        unique_map.values(),
        key=lambda x: (x['person_role'].person.first_name, x['person_role'].person.last_name)
    )

    # 3. Build Filter Summary for Header
    filter_info = []
    if search_supervisor:
        filter_info.append(f"Search: {search_supervisor}")

    if is_active_supervisor is not None:
        filter_info.append(f"Supervisor Status: {'Active' if is_active_supervisor else 'Inactive'}")

    if is_active_student is not None:
        filter_info.append(f"Supervisee Status: {'Active' if is_active_student else 'Inactive'}")

    if is_main is not None:
        filter_info.append("Type: Main Supervisors Only" if is_main else "Type: Co-supervisors Only")

    if cohort_number:
        filter_info.append(f"Cohort: {cohort_number}")

    # Resolve Role IDs to Names for the header
    if supervisor_role_id:
        role = db.query(models.Role).filter_by(id=supervisor_role_id).first()
        if role:
            filter_info.append(f"Supervisor Role: {role.role}")

    if supervisee_role_id:
        role = db.query(models.Role).filter_by(id=supervisee_role_id).first()
        if role:
            filter_info.append(f"Supervisee Role: {role.role}")

    # 4. Format Data for Excel
    data_to_export = []
    for item in aggregated_list:
        pr = item['person_role']
        person = pr.person

        raw_role = pr.role.role
        role_str = raw_role.value if hasattr(raw_role, 'value') else str(raw_role)
        role_display = role_str.title()

        data_to_export.append({
            "Main?": "Yes" if item['is_main'] else "No",
            "Role": role_display,
            "Name": f"{person.first_name} {person.last_name}",
            "Email": person.email,
            "Start Date": pr.start_date.strftime("%Y-%m-%d") if pr.start_date else "",
            "End Date": pr.end_date.strftime("%Y-%m-%d") if pr.end_date else ""
        })

    headers = ["Main?", "Role", "Name", "Email", "Start Date", "End Date"]

    # 5. Generate and Return
    excel_buffer = generate_excel_response(
        data_to_export,
        headers,
        "Supervisors Report",
        filter_info=filter_info
    )

    # filename = f"supervisors_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    filename = f"supervisors_report.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/reports/supervisions/export/emails")
def export_supervisors_emails(
        is_main: Optional[bool] = Query(None),
        is_active_supervisor: Optional[bool] = Query(None),
        is_active_student: Optional[bool] = Query(None),
        supervisor_role_id: Optional[int] = Query(None),
        supervisee_role_id: Optional[int] = Query(None),
        cohort_number: Optional[int] = Query(None),
        search_supervisor: Optional[str] = Query(None),

        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),
):
    """
    Generate a JSON list of emails for the Supervisors Report.
    """
    logger.info(f"{current_user.username} fetching supervisors emails")

    # 1. Fetch Raw Data
    links = crud.report_supervisions(
        db,
        is_main=is_main,
        is_active_supervisor=is_active_supervisor,
        is_active_student=is_active_student,
        supervisor_role_id=supervisor_role_id,
        supervisee_role_id=supervisee_role_id,
        cohort_number=cohort_number,
        search_supervisor=search_supervisor
    )

    # 2. Aggregate Unique Supervisors
    unique_supervisors = {}
    for link in links:
        # We only need the ID to ensure uniqueness here
        unique_supervisors[link.supervisor_role_id] = link.supervisor

    # 3. Build Filter Summary (Same logic as above)
    filter_info = []
    if search_supervisor: filter_info.append(f"Search: {search_supervisor}")
    if is_active_supervisor is not None: filter_info.append(
        f"Supervisor Status: {'Active' if is_active_supervisor else 'Inactive'}")
    if is_active_student is not None: filter_info.append(
        f"Supervisee Status: {'Active' if is_active_student else 'Inactive'}")
    if is_main is not None: filter_info.append(
        "Type: Main Supervisors Only" if is_main else "Type: Co-supervisors Only")
    if cohort_number: filter_info.append(f"Cohort: {cohort_number}")

    if supervisor_role_id:
        role = db.query(models.Role).filter_by(id=supervisor_role_id).first()
        if role: filter_info.append(f"Supervisor Role: {role.role}")
    if supervisee_role_id:
        role = db.query(models.Role).filter_by(id=supervisee_role_id).first()
        if role: filter_info.append(f"Supervisee Role: {role.role}")

    # 4. Extract Emails
    emails = [
        sup.person.email
        for sup in unique_supervisors.values()
        if sup.person.email
    ]

    # 5. Return JSON
    return {
        "count": len(emails),
        "filter_summary": filter_info,
        "emails": emails
    }


# </editor-fold>

# <editor-fold desc="Report Project Leaders endpoints">
# --- Project Leaders ---

@router.get(
    "/reports/project-leaders/",
    response_model=List[schemas.ProjectPersonRoleRead],
    summary="Search and Filter Project Leaders for Reports"
)
def get_project_leaders_report(
        # Person Filters
        search: Optional[str] = Query(None, description="Search by person's first or last name"),
        is_active_person_role: Optional[bool] = Query(None, description="Filter by active status of the PersonRole"),
        person_role_id: Optional[int] = Query(None, description="Filter by generic role (Researcher/Postdoc/etc)"),

        # Membership Filters
        is_pi_only: Optional[bool] = Query(None, description="Filter: Only Principal Investigators"),
        is_contact_only: Optional[bool] = Query(None, description="Filter: Only Contact Persons"),

        # Project Filters
        call_type_id: Optional[int] = Query(None, description="Filter by Project Call Type"),
        project_status: Optional[str] = Query(None,
                                              description="Filter by Project Status (ongoing, awaiting_report, completed)"),

        # Dependencies
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),
):
    """
    Generates a list of Project Leaders (PIs and Contact Persons).
    Returns a list of membership links (Person <-> Project).
    Frontend should handle aggregation of unique people.
    """
    logger.info(f"{current_user.username} accessing project leaders report")

    return crud.report_project_leaders(
        db,
        search=search,
        is_active_person_role=is_active_person_role,
        person_role_id=person_role_id,
        is_pi_only=is_pi_only,
        is_contact_only=is_contact_only,
        call_type_id=call_type_id,
        project_status=project_status
    )


@router.get("/reports/project-leaders/export/excel")
def export_project_leaders_to_excel(
        search: Optional[str] = Query(None),
        is_active_person_role: Optional[bool] = Query(None),
        person_role_id: Optional[int] = Query(None),
        is_pi_only: Optional[bool] = Query(None),
        is_contact_only: Optional[bool] = Query(None),
        call_type_id: Optional[int] = Query(None),
        project_status: Optional[str] = Query(None),

        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),
):
    """
    Export the Project Leaders Report to Excel.
    Aggregates membership links into unique people.
    """
    logger.info(f"{current_user.username} exporting project leaders report to Excel")

    # 1. Fetch Raw Data
    links = crud.report_project_leaders(
        db,
        search=search,
        is_active_person_role=is_active_person_role,
        person_role_id=person_role_id,
        is_pi_only=is_pi_only,
        is_contact_only=is_contact_only,
        call_type_id=call_type_id,
        project_status=project_status
    )

    # 2. Aggregation Logic (Links -> Unique People)
    # Map: person_role_id -> { 'person_role': obj, 'is_pi': bool, 'is_contact': bool }
    unique_map = {}
    for link in links:
        pr_id = link.person_role_id
        if pr_id not in unique_map:
            unique_map[pr_id] = {
                "person_role": link.person_role,
                "is_pi": link.is_principal_investigator,
                "is_contact": link.is_contact_person
            }
        else:
            # Apply OR logic: if they are PI/Contact in ANY of the filtered projects, mark as Yes
            unique_map[pr_id]["is_pi"] = unique_map[pr_id]["is_pi"] or link.is_principal_investigator
            unique_map[pr_id]["is_contact"] = unique_map[pr_id]["is_contact"] or link.is_contact_person

    # Sort aggregated list by name
    aggregated_list = sorted(
        unique_map.values(),
        key=lambda x: (x['person_role'].person.first_name, x['person_role'].person.last_name)
    )

    # 3. Build Filter Summary for Header
    filter_info = []
    if search: filter_info.append(f"Search: {search}")

    if is_active_person_role is not None:
        filter_info.append(f"Person Status: {'Active' if is_active_person_role else 'Inactive'}")

    if person_role_id:
        role = db.query(models.Role).filter_by(id=person_role_id).first()
        if role: filter_info.append(f"Role: {role.role}")

    # Membership filters
    if is_pi_only: filter_info.append("Project Role: Principal Investigators Only")
    if is_contact_only: filter_info.append("Project Role: Contact Persons Only")

    # Project filters
    if call_type_id:
        ct = db.query(models.ProjectCallType).filter_by(id=call_type_id).first()
        if ct: filter_info.append(f"Project Call Type: {ct.type}")

    if project_status:
        # Prettify status string (e.g., 'awaiting_report' -> 'Awaiting Report')
        status_display = project_status.replace('_', ' ').title()
        filter_info.append(f"Project Status: {status_display}")

    # 4. Format Data for Excel
    data_to_export = []
    for item in aggregated_list:
        pr = item['person_role']
        person = pr.person

        # Handle Enum to String conversion
        raw_role = pr.role.role
        role_str = raw_role.value if hasattr(raw_role, 'value') else str(raw_role)
        role_display = role_str.title()

        data_to_export.append({
            "PI?": "Yes" if item['is_pi'] else "No",
            "Contact Person?": "Yes" if item['is_contact'] else "No",
            "Role": role_display,
            "Name": f"{person.first_name} {person.last_name}",
            "Email": person.email,
            "Start Date": pr.start_date.strftime("%Y-%m-%d") if pr.start_date else "",
            "End Date": pr.end_date.strftime("%Y-%m-%d") if pr.end_date else ""
        })

    headers = ["PI?", "Contact Person?", "Role", "Name", "Email", "Start Date", "End Date"]

    # 5. Generate and Return
    excel_buffer = generate_excel_response(
        data_to_export,
        headers,
        "Project Leaders Report",
        filter_info=filter_info
    )

    # filename = f"project_leaders_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    filename = f"project_leaders_report.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/reports/project-leaders/export/emails")
def export_project_leaders_emails(
        search: Optional[str] = Query(None),
        is_active_person_role: Optional[bool] = Query(None),
        person_role_id: Optional[int] = Query(None),
        is_pi_only: Optional[bool] = Query(None),
        is_contact_only: Optional[bool] = Query(None),
        call_type_id: Optional[int] = Query(None),
        project_status: Optional[str] = Query(None),

        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),
):
    """
    Generate a JSON list of emails for the Project Leaders Report.
    """
    logger.info(f"{current_user.username} fetching project leaders emails")

    # 1. Fetch Raw Data
    links = crud.report_project_leaders(
        db,
        search=search,
        is_active_person_role=is_active_person_role,
        person_role_id=person_role_id,
        is_pi_only=is_pi_only,
        is_contact_only=is_contact_only,
        call_type_id=call_type_id,
        project_status=project_status
    )

    # 2. Aggregate Unique People (using ID as key to prevent duplicates)
    unique_people = {}
    for link in links:
        unique_people[link.person_role_id] = link.person_role.person

    # 3. Build Filter Summary (Reusing the same logic blocks as above for headers)
    filter_info = []
    if search: filter_info.append(f"Search: {search}")
    if is_active_person_role is not None: filter_info.append(
        f"Person Status: {'Active' if is_active_person_role else 'Inactive'}")
    if person_role_id:
        role = db.query(models.Role).filter_by(id=person_role_id).first()
        if role: filter_info.append(f"Role: {role.role}")
    if is_pi_only: filter_info.append("Project Role: Principal Investigators Only")
    if is_contact_only: filter_info.append("Project Role: Contact Persons Only")
    if call_type_id:
        ct = db.query(models.ProjectCallType).filter_by(id=call_type_id).first()
        if ct: filter_info.append(f"Project Call Type: {ct.type}")
    if project_status:
        status_display = project_status.replace('_', ' ').title()
        filter_info.append(f"Project Status: {status_display}")

    # 4. Extract Emails
    emails = [
        p.email for p in unique_people.values() if p.email
    ]

    # 5. Return JSON
    return {
        "count": len(emails),
        "filter_summary": filter_info,
        "emails": emails
    }


# </editor-fold>

# <editor-fold desc="Report Semester Abroad endpoints">
# --- Semester Abroad ---

@router.get(
    "/reports/semester-abroad-data/",
    response_model=List[schemas.StudentActivityReportRead],
    summary="Search and Filter Semester Abroad Activities"
)
def get_semester_abroad_report(
        is_active_student: Optional[bool] = Query(None, description="Filter by active status of the PhD Student"),
        activity_status: Optional[str] = Query(None, description="Filter by Activity Status (ongoing, completed)"),

        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),
):
    """
    Generates a list of Semester Abroad activities.
    One row per activity.
    """
    logger.info(f"{current_user.username} accessing semester abroad report")

    return crud.report_semester_abroad(
        db,
        is_active_student=is_active_student,
        activity_status=activity_status
    )


@router.get("/reports/semester-abroad-data/export/excel")
def export_semester_abroad_to_excel(
        is_active_student: Optional[bool] = Query(None),
        activity_status: Optional[str] = Query(None),

        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user),
):
    """
    Export the Semester Abroad Report to Excel.
    """
    logger.info(f"{current_user.username} exporting semester abroad report to Excel")

    # 1. Fetch Data
    activities = crud.report_semester_abroad(
        db,
        is_active_student=is_active_student,
        activity_status=activity_status
    )

    # 2. Build Filter Summary
    filter_info = []
    if is_active_student is not None:
        filter_info.append(f"Student Status: {'Active' if is_active_student else 'Inactive'}")

    if activity_status:
        # Prettify string (e.g. 'ongoing' -> 'Ongoing')
        filter_info.append(f"Activity Status: {activity_status.title()}")

    # 3. Format Data
    data_to_export = []
    for act in activities:
        # Navigate relationships: Activity -> Student -> PersonRole -> Person
        student = act.student
        person = student.person_role.person

        data_to_export.append({
            "Host Institution": act.host_institution or "",
            "City": act.city or "",
            "Country": act.country or "",
            "Description": act.description or "",
            "PhD Student": f"{person.first_name} {person.last_name}",
            "Email": person.email,
            "Start Date": act.start_date.strftime("%Y-%m-%d") if act.start_date else "",
            "End Date": act.end_date.strftime("%Y-%m-%d") if act.end_date else ""
        })

    headers = ["Host Institution", "City", "Country", "Description", "PhD Student", "Email", "Start Date", "End Date"]

    # 4. Generate and Return
    excel_buffer = generate_excel_response(
        data_to_export,
        headers,
        "Semester Abroad Report",
        filter_info=filter_info
    )

    # filename = f"semester_abroad_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    filename = f"semester_abroad_report.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# </editor-fold>
