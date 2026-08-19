import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi import status, BackgroundTasks
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies, models, tasks
from ..crud import EntityNotFoundError
from ..excel_utils import generate_excel_response
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["academic_publications"])
logger = logging.getLogger(__name__)


# <editor-fold desc="Academic Publication endpoints">
# --- Academic Publication endpoints ---

@router.get("/academic-publications/{pub_id}", response_model=schemas.AcademicPublicationRead)
def read_academic_publication(
    pub_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    pub = crud.get_academic_publication(db, pub_id)
    if not pub:
        logger.warning(f"Academic Publication #{pub_id} not found")
        raise HTTPException(404, f"Academic Publication #{pub_id} not found")

    logger.info(f"{current_user.username} fetched academic publication #{pub_id}")
    return pub


@router.get("/academic-publications/", response_model=List[schemas.AcademicPublicationRead])
def list_academic_publications(
    published_year:  Optional[int] = Query(None),
    is_duplicate:    Optional[bool] = Query(None),
    ai_recommendation: Optional[models.AIRecommendation] = Query(None),
    is_relevant:     Optional[bool] = Query(None),
    is_reviewed:     Optional[bool] = Query(None),
    # is_pushed_to_wp: Optional[bool] = Query(None),
    is_published_to_wp: Optional[bool] = Query(None),
    has_processing_error: Optional[bool] = Query(None),
    search:          Optional[str] = Query(None, description="Substring search on title or journal"),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed academic publications (year={published_year}, "
                f"is_duplicate={is_duplicate}, ai_recommendation={ai_recommendation}, "
                f"is_relevant={is_relevant}, is_reviewed={is_reviewed}, "
                f"is_published_to_wp={is_published_to_wp}, "
                f"has_processing_error={has_processing_error}, search={search!r})")
    return crud.list_academic_publications(
        db,
        published_year=published_year,
        is_duplicate=is_duplicate,
        ai_recommendation=ai_recommendation,
        is_relevant=is_relevant,
        is_reviewed=is_reviewed,
        # is_pushed_to_wp=is_pushed_to_wp,
        is_published_to_wp=is_published_to_wp,
        has_processing_error=has_processing_error,
        search=search
    )


@router.post("/academic-publications/", response_model=schemas.AcademicPublicationRead)
def create_academic_publication(
    pub_in: schemas.AcademicPublicationCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} creating academic publication '{pub_in.title}'")
    try:
        return crud.create_academic_publication(db, pub_in)
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/academic-publications/{pub_id}", response_model=schemas.AcademicPublicationRead)
def update_academic_publication(
    pub_id: int,
    pub_in: schemas.AcademicPublicationUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating academic publication {pub_id} → {pub_in}")
    try:
        return crud.update_academic_publication(db, pub_id, pub_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/academic-publications/{pub_id}", status_code=204)
def delete_academic_publication(
    pub_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} deleting academic publication {pub_id}")
    try:
        crud.delete_academic_publication(db, pub_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)

# </editor-fold>

# <editor-fold desc="Academic Publication relationships endpoints">
# --- People Roles ---

@router.get("/academic-publications/{pub_id}/people-roles/", response_model=List[schemas.AcademicPublicationPersonRoleRead])
def list_academic_publication_people_roles(
    pub_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing people roles for academic publication {pub_id}")
    try:
        return crud.get_academic_publication_person_roles(db, pub_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.post("/academic-publications/{pub_id}/people-roles/", response_model=schemas.AcademicPublicationPersonRoleRead)
def add_academic_publication_person_role(
    pub_id: int,
    link: schemas.AcademicPublicationPersonRoleLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking person role {link.person_role_id} → academic publication {pub_id}")
    try:
        return crud.add_person_role_to_academic_publication(db, pub_id, link)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/academic-publications/{pub_id}/people-roles/{person_role_id}", status_code=204)
def remove_academic_publication_person_role(
    pub_id: int,
    person_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking person role {person_role_id} from academic publication {pub_id}")
    try:
        crud.remove_person_role_from_academic_publication(db, pub_id, person_role_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)

# </editor-fold>

# <editor-fold desc="Academic Publication Automation & Actions endpoints">
# --- Automation Actions (Placeholders) ---

@router.post("/academic-publications/actions/sync-swepub", status_code=status.HTTP_202_ACCEPTED)
def sync_swepub(
        background_tasks: BackgroundTasks,
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    """Trigger API fetch from SwePub based on active researchers."""

    # 1. Synchronous lock check for immediate UI feedback
    active_job = db.query(models.AutomationLog).filter(
        models.AutomationLog.action_type == models.ActionType.ACADEMIC_SYNC,
        models.AutomationLog.status == models.ActionStatus.IN_PROGRESS
    ).first()

    if active_job:
        # Check if the lock is actually active (less than 2 hours old)
        now = datetime.now(timezone.utc)
        job_time = active_job.timestamp if active_job.timestamp.tzinfo else active_job.timestamp.replace(
            tzinfo=timezone.utc)

        if (now - job_time) < timedelta(hours=2):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A SwePub synchronization job is already running."
            )
        # If it's older than 2 hours, tasks.py TTL logic will safely clear it.

    # 2. Hand off to the background task orchestrator
    background_tasks.add_task(tasks.sync_swepub_task, user_id=current_user.id)

    logger.info(f"User {current_user.username} triggered SwePub sync (spawned in background).")

    return {"message": "SwePub synchronization started in the background."}


@router.post("/academic-publications/actions/process-pending", status_code=status.HTTP_202_ACCEPTED)
def process_pending_academic(
        background_tasks: BackgroundTasks,
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    """Trigger evaluation, deduplication, and entity matching for unreviewed academic items."""

    # 1. Synchronous lock check for immediate UI feedback
    active_job = db.query(models.AutomationLog).filter(
        models.AutomationLog.action_type == models.ActionType.ACADEMIC_PROCESSING,
        models.AutomationLog.status == models.ActionStatus.IN_PROGRESS
    ).first()

    if active_job:
        # Check if the lock is actually active (less than 2 hours old)
        now = datetime.now(timezone.utc)
        job_time = active_job.timestamp if active_job.timestamp.tzinfo else active_job.timestamp.replace(
            tzinfo=timezone.utc)

        if (now - job_time) < timedelta(hours=2):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An academic processing job is already running."
            )
        # If it's older than 2 hours, tasks.py TTL logic will safely clear it.

    # 2. Hand off to the background task orchestrator
    background_tasks.add_task(tasks.process_pending_academic_task, user_id=current_user.id)

    logger.info(f"User {current_user.username} triggered academic processing (spawned in background).")

    return {"message": "Academic processing started in the background."}


@router.post("/academic-publications/actions/push-to-wp", status_code=status.HTTP_202_ACCEPTED)
def push_approved_academic_to_wp(
        background_tasks: BackgroundTasks,
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    """Trigger background push of approved academic publications to WordPress."""

    # 1. Synchronous lock check for immediate UI feedback
    active_job = db.query(models.AutomationLog).filter(
        models.AutomationLog.action_type == models.ActionType.ACADEMIC_PUBLISH,
        models.AutomationLog.status == models.ActionStatus.IN_PROGRESS
    ).first()

    if active_job:
        # Check if the lock is actually active (less than 2 hours old)
        now = datetime.now(timezone.utc)
        job_time = active_job.timestamp if active_job.timestamp.tzinfo else active_job.timestamp.replace(
            tzinfo=timezone.utc)

        if (now - job_time) < timedelta(hours=2):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A WordPress push job for academic publications is already running."
            )
        # If it's older than 2 hours, tasks.py TTL logic will safely clear it.

    # 2. Hand off to the background task orchestrator
    background_tasks.add_task(tasks.push_approved_academic_task, user_id=current_user.id)

    logger.info(f"User {current_user.username} triggered academic WordPress push (spawned in background).")

    return {"message": "WordPress push for academic publications started in the background."}

# </editor-fold>

# <editor-fold desc="Academic Publication Export endpoints">
# --- Exports ---

@router.get("/academic-publications/export/academic.xlsx")
def export_academic_to_excel(
    published_year:  Optional[int] = Query(None),
    is_relevant:     Optional[bool] = Query(None),
    is_reviewed:     Optional[bool] = Query(None),
    is_pushed_to_wp: Optional[bool] = Query(None),
    search:          Optional[str] = Query(None),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    """Placeholder: Export filtered academic publications to Excel."""
    logger.info(f"{current_user.username} exporting academic publications")
    # Implementation will mirror project.py export logic using crud.list_academic_publications
    raise HTTPException(501, "Export functionality not yet implemented for academic publications")

# </editor-fold>
