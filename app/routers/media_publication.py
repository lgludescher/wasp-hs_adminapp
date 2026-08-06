import logging
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Query, UploadFile, File
from fastapi import status, BackgroundTasks
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies, models, tasks
from ..crud import EntityNotFoundError
from ..excel_utils import generate_excel_response
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["media_publications"])
logger = logging.getLogger(__name__)


# <editor-fold desc="Media Publication endpoints">
# --- Media Publication endpoints ---

@router.get("/media-publications/{pub_id}", response_model=schemas.MediaPublicationRead)
def read_media_publication(
    pub_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    pub = crud.get_media_publication(db, pub_id)
    if not pub:
        logger.warning(f"Media Publication #{pub_id} not found")
        raise HTTPException(404, f"Media Publication #{pub_id} not found")

    logger.info(f"{current_user.username} fetched media publication #{pub_id}")
    return pub


@router.get("/media-publications/", response_model=List[schemas.MediaPublicationRead])
def list_media_publications(
    platform:        Optional[models.MediaPlatform] = Query(None),
    is_duplicate:    Optional[bool] = Query(None),
    is_relevant:     Optional[bool] = Query(None),
    is_reviewed:     Optional[bool] = Query(None),
    is_pushed_to_wp: Optional[bool] = Query(None),
    search:          Optional[str] = Query(None, description="Substring search on title or source"),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed media publications (platform={platform}, "
                f"is_duplicate={is_duplicate}, is_relevant={is_relevant}, is_reviewed={is_reviewed}, "
                f"is_pushed_to_wp={is_pushed_to_wp}, search={search!r})")
    return crud.list_media_publications(
        db,
        platform=platform,
        is_duplicate=is_duplicate,
        is_relevant=is_relevant,
        is_reviewed=is_reviewed,
        is_pushed_to_wp=is_pushed_to_wp,
        search=search
    )


@router.post("/media-publications/", response_model=schemas.MediaPublicationRead)
def create_media_publication(
    pub_in: schemas.MediaPublicationCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} creating media publication '{pub_in.title}'")
    try:
        return crud.create_media_publication(db, pub_in)
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/media-publications/{pub_id}", response_model=schemas.MediaPublicationRead)
def update_media_publication(
    pub_id: int,
    pub_in: schemas.MediaPublicationUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating media publication {pub_id} → {pub_in}")
    try:
        return crud.update_media_publication(db, pub_id, pub_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/media-publications/{pub_id}", status_code=204)
def delete_media_publication(
    pub_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} deleting media publication {pub_id}")
    try:
        crud.delete_media_publication(db, pub_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)

# </editor-fold>

# <editor-fold desc="Media Publication relationships endpoints">
# --- People Roles ---

@router.get("/media-publications/{pub_id}/people-roles/", response_model=List[schemas.MediaPublicationPersonRoleRead])
def list_media_publication_people_roles(
    pub_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing people roles for media publication {pub_id}")
    try:
        return crud.get_media_publication_person_roles(db, pub_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.post("/media-publications/{pub_id}/people-roles/", response_model=schemas.MediaPublicationPersonRoleRead)
def add_media_publication_person_role(
    pub_id: int,
    link: schemas.MediaPublicationPersonRoleLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking person role {link.person_role_id} → media publication {pub_id}")
    try:
        return crud.add_person_role_to_media_publication(db, pub_id, link)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/media-publications/{pub_id}/people-roles/{person_role_id}", status_code=204)
def remove_media_publication_person_role(
    pub_id: int,
    person_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking person role {person_role_id} from media publication {pub_id}")
    try:
        crud.remove_person_role_from_media_publication(db, pub_id, person_role_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)

# </editor-fold>

# <editor-fold desc="Media Publication Automation & Actions endpoints">
# --- Automation Actions (Placeholders) ---

@router.post("/media-publications/actions/upload", response_model=schemas.MediaUploadSummary)
async def upload_media_file(
        file: UploadFile = File(...),
        dry_run: bool = Query(False, description="Parse and check duplicates without saving to DB"),
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} triggered file upload for {file.filename} (dry_run={dry_run})")

    # 1. Read file content
    content = await file.read()

    # 2. Parse file
    try:
        from ..services.media_parser import parse_uploaded_file
        parsed_items = parse_uploaded_file(content, file.filename)
    except Exception as e:
        logger.error(f"Failed to parse file: {e}")
        # Log failure if not a dry run
        if not dry_run:
            # Infer the attempted platform from the file extension since parsing failed
            is_factiva = file.filename and file.filename.lower().endswith('.rtf')
            action_type = (models.ActionType.MEDIA_INGESTION_FACTIVA
                           if is_factiva
                           else models.ActionType.MEDIA_INGESTION_RETRIEVER)

            log_in = schemas.AutomationLogCreate(
                action_type=action_type,
                trigger_source=models.TriggerSource.MANUAL,
                status=models.ActionStatus.FAILED,
                user_id=current_user.id,
                items_processed=0,
                error_message=f"Parsing failed: {str(e)}"
            )
            crud.create_automation_log(db, log_in)

        raise HTTPException(400, f"File parsing failed: {str(e)}")

    if not parsed_items:
        raise HTTPException(400, "The file was parsed successfully, but no valid articles were found.")

    # Dynamically grab the platform from the parser's output
    detected_platform = parsed_items[0].platform

    # 3. Process Items
    new_saved = 0
    duplicates = 0
    errors = 0
    error_details = []

    for item in parsed_items:
        # Type 1 Duplicate Check (Exact Ingestion Duplicate)
        is_dup = False
        if item.external_id:
            existing = db.query(models.MediaPublication).filter(
                models.MediaPublication.external_id == item.external_id
            ).first()
            if existing:
                is_dup = True

        if is_dup:
            duplicates += 1
            continue

        if dry_run:
            new_saved += 1  # Count what *would* be saved
            continue

        # Attempt to save to DB (Option B: Partial Saves)
        try:
            crud.create_media_publication(db, item)
            new_saved += 1
        except Exception as e:
            logger.warning(f"Failed to save item '{item.title}': {e}")
            errors += 1
            error_details.append(f"Item '{item.title[:30]}...': {str(e)}")
            # Crucial: Rollback the session so the loop can safely continue
            # without carrying the broken transaction forward.
            db.rollback()

    # 4. Create Automation Log
    if not dry_run:
        action_status = models.ActionStatus.SUCCESS
        if errors > 0:
            action_status = models.ActionStatus.PARTIAL if new_saved > 0 else models.ActionStatus.FAILED

        action_type = (models.ActionType.MEDIA_INGESTION_FACTIVA
                       if detected_platform == models.MediaPlatform.FACTIVA
                       else models.ActionType.MEDIA_INGESTION_RETRIEVER)

        log_in = schemas.AutomationLogCreate(
            action_type=action_type,
            trigger_source=models.TriggerSource.MANUAL,
            status=action_status,
            user_id=current_user.id,
            items_processed=new_saved,
            # Truncate error message to avoid overflowing DB text limits
            error_message="; ".join(error_details)[:2000] if error_details else None
        )
        crud.create_automation_log(db, log_in)

    return schemas.MediaUploadSummary(
        status="success" if errors == 0 else "partial_success",
        filename=file.filename,
        platform=detected_platform,
        total_parsed=len(parsed_items),
        new_saved=new_saved,
        duplicates_skipped=duplicates,
        errors=errors,
        error_details=error_details,
        dry_run=dry_run
    )


@router.post("/media-publications/actions/process-pending", status_code=status.HTTP_202_ACCEPTED)
def process_pending_media(
        background_tasks: BackgroundTasks,
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    """Trigger background processing (Scrape, Deduplicate, LLM) for pending media."""

    # 1. Synchronous lock check for immediate UI feedback
    active_job = db.query(models.AutomationLog).filter(
        models.AutomationLog.action_type == models.ActionType.MEDIA_PROCESSING,
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
                detail="A media processing job is already running."
            )
        # If it's older than 2 hours, we let the tasks.py TTL logic safely clear it out.

    # 2. Hand off to the background task orchestrator
    background_tasks.add_task(tasks.process_pending_media_task, user_id=current_user.id)

    logger.info(f"User {current_user.username} triggered media processing (spawned in background).")

    return {"message": "Media processing started in the background."}


@router.post("/media-publications/actions/push-to-wp", status_code=status.HTTP_202_ACCEPTED)
def push_approved_media_to_wp(
        background_tasks: BackgroundTasks,
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    """Trigger background push of approved media articles to WordPress."""

    # 1. Synchronous lock check for immediate UI feedback
    active_job = db.query(models.AutomationLog).filter(
        models.AutomationLog.action_type == models.ActionType.MEDIA_PUBLISH,
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
                detail="A WordPress push job for media is already running."
            )
        # If it's older than 2 hours, tasks.py TTL logic will safely clear it.

    # 2. Hand off to the background task orchestrator
    background_tasks.add_task(tasks.push_approved_media_task, user_id=current_user.id)

    logger.info(f"User {current_user.username} triggered media WordPress push (spawned in background).")

    return {"message": "WordPress push for media started in the background."}

# </editor-fold>

# <editor-fold desc="Media Publication Export endpoints">
# --- Exports ---

@router.get("/media-publications/export/media.xlsx")
def export_media_to_excel(
    platform:        Optional[models.MediaPlatform] = Query(None),
    is_relevant:     Optional[bool] = Query(None),
    is_reviewed:     Optional[bool] = Query(None),
    is_pushed_to_wp: Optional[bool] = Query(None),
    search:          Optional[str] = Query(None),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    """Placeholder: Export filtered media to Excel."""
    logger.info(f"{current_user.username} exporting media publications")
    # Implementation will mirror project.py export logic using crud.list_media_publications
    raise HTTPException(501, "Export functionality not yet implemented for media publications")

# </editor-fold>
