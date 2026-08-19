import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

# Adjust imports based on your actual project structure
from app.database import SessionLocal
from app import models, schemas, crud

logger = logging.getLogger(__name__)


# ==========================================
# LOCK & LOG MANAGEMENT HELPERS
# ==========================================

def _manage_job_lock(db: Session, action_type: models.ActionType, user_id: int) -> models.AutomationLog:
    """
    Checks for existing IN_PROGRESS locks. Clears "ghost" locks older than 2 hours.
    Returns a new AutomationLog(status=IN_PROGRESS) if safe to proceed.
    Raises ValueError if the job is already actively running.
    """
    # 1. Look for existing IN_PROGRESS jobs for this specific action
    active_jobs = db.query(models.AutomationLog).filter(
        models.AutomationLog.action_type == action_type,
        models.AutomationLog.status == models.ActionStatus.IN_PROGRESS
    ).all()

    for job in active_jobs:
        # Check Time-To-Live (TTL) to catch orphaned locks from crashes.
        # Now correctly uses the 'timestamp' column.
        now = datetime.now(timezone.utc)

        # Ensure timestamp has timezone info before doing the math
        job_time = job.timestamp if job.timestamp.tzinfo else job.timestamp.replace(tzinfo=timezone.utc)
        job_age = now - job_time

        if job_age > timedelta(hours=2):
            logger.warning(f"Found orphaned lock for {action_type} (ID: {job.id}). Marking as FAILED.")

            # Use CRUD to update the ghost lock
            log_update = schemas.AutomationLogUpdate(
                status=models.ActionStatus.FAILED,
                error_message="Job timed out (orphaned lock cleared by system)."
            )
            crud.update_automation_log(db, log_id=job.id, log_in=log_update)
        else:
            raise ValueError(f"A {action_type} job is currently running.")

    # 2. Safe to proceed: Create the new IN_PROGRESS lock
    log_in = schemas.AutomationLogCreate(
        action_type=action_type,
        trigger_source=models.TriggerSource.MANUAL,
        status=models.ActionStatus.IN_PROGRESS,
        user_id=user_id,
        items_processed=0
    )
    return crud.create_automation_log(db, log_in)


def _finalize_job(db: Session, log_id: int, status: models.ActionStatus, processed: int, error: str = None):
    """Safely closes the job state in the database using existing CRUD functions."""
    log_update = schemas.AutomationLogUpdate(
        status=status,
        items_processed=processed,
        error_message=error[:2000] if error else None
    )
    try:
        crud.update_automation_log(db, log_id=log_id, log_in=log_update)
    except Exception as e:
        logger.error(f"Failed to finalize automation log {log_id}: {e}")


# ==========================================
# 1. ACADEMIC INGESTION: SWEPUB SYNC
# ==========================================

def sync_swepub_task(user_id: int):
    """Background task: Connects to SwePub API and saves new abstracts."""
    db = SessionLocal()
    job_log = None
    items_saved = 0

    try:
        job_log = _manage_job_lock(db, models.ActionType.ACADEMIC_SYNC, user_id)

        # MODIFICATION: Implemented Delta Sync lookup. We query the automation log
        # for the last successful sync timestamp so we don't fetch the whole DB.
        last_sync = crud.get_latest_automation_log(db, models.ActionType.ACADEMIC_SYNC, models.ActionStatus.SUCCESS)
        last_sync_time = last_sync.timestamp if last_sync else None

        # TODO: Phase 1 - Fetch from SwePub API (pass last_sync_time as parameter)
        # from app.services.swepub import fetch_recent_publications
        # raw_data = fetch_recent_publications(since=last_sync_time)

        # TODO: Phase 2 - Save to DB (checking for Type 1 exact ingestion duplicates)
        # items_saved = save_swepub_to_db(db, raw_data)

        _finalize_job(db, job_log.id, models.ActionStatus.SUCCESS, items_saved)

    except ValueError as e:
        logger.warning(str(e))  # Blocked by lock, silently abort
    except Exception as e:
        logger.error(f"SwePub Sync Failed: {e}")
        db.rollback()
        if job_log:
            _finalize_job(db, job_log.id, models.ActionStatus.FAILED, items_saved, str(e))
    finally:
        db.close()


# ==========================================
# 2. MEDIA PROCESSING ORCHESTRATOR
# ==========================================

def process_pending_media_task(user_id: int):
    """Background task: Scrapes URLs, Deduplicates, AI Evaluation, Entity Matching."""
    db = SessionLocal()
    job_log = None
    items_processed = 0

    try:
        job_log = _manage_job_lock(db, models.ActionType.MEDIA_PROCESSING, user_id)

        # ---------------------------------------------------------
        # PHASE 1: SCRAPER (Missing Body & Has URL)
        # ---------------------------------------------------------
        # MODIFICATION: Added `is_scraped == False` to prevent empty-body infinite loops.
        # Added `has_processing_error == False` to ignore quarantined items.
        items_to_scrape = db.query(models.MediaPublication).filter(
            models.MediaPublication.content_url.isnot(None),
            models.MediaPublication.article_body.is_(None),
            models.MediaPublication.is_scraped == False,
            models.MediaPublication.has_processing_error == False
        ).all()

        if items_to_scrape:
            # TODO: from app.services.scraper import scrape_urls
            # items_processed += scrape_urls(db, items_to_scrape)
            pass

        # ---------------------------------------------------------
        # PHASE 2: DEDUPLICATION (Body Exists & Duplication Unknown)
        # ---------------------------------------------------------
        # MODIFICATION: Added quarantine guard.
        items_to_dedup = db.query(models.MediaPublication).filter(
            models.MediaPublication.article_body.isnot(None),
            models.MediaPublication.is_duplicate.is_(None),
            models.MediaPublication.has_processing_error == False
        ).all()

        if items_to_dedup:
            # TODO: from app.services.deduplicator import flag_duplicates
            # flag_duplicates(db, items_to_dedup)
            pass

        # ---------------------------------------------------------
        # PHASE 3: LLM EVALUATION (Not a Duplicate & Evaluation Unknown)
        # ---------------------------------------------------------
        # MODIFICATION: Changed trigger to `ai_recommendation` (to avoid overriding human review)
        # and added quarantine guard.
        items_to_eval = db.query(models.MediaPublication).filter(
            models.MediaPublication.is_duplicate == False,
            models.MediaPublication.ai_recommendation.is_(None),
            models.MediaPublication.has_processing_error == False
        ).all()

        if items_to_eval:
            # TODO: from app.services.llm import evaluate_media
            # evaluate_media(db, items_to_eval)
            items_processed += len(items_to_eval)

        # ---------------------------------------------------------
        # PHASE 4: ENTITY MATCHING (Is Relevant & Not Yet Matched)
        # ---------------------------------------------------------
        # MODIFICATION: Changed to Post-Review trigger to save API calls.
        # It only runs if a human has reviewed it, it's relevant, and not matched yet.
        """
        # Placeholder for future implementation
        items_to_match = db.query(models.MediaPublication).filter(
            models.MediaPublication.is_reviewed == True,
            models.MediaPublication.is_relevant == True,
            models.MediaPublication.entities_matched.is_(None),
            models.MediaPublication.has_processing_error == False
        ).all()

        if items_to_match:
            # from app.services.entity_matcher import link_media_entities
            # link_media_entities(db, items_to_match)
            pass
        """

        _finalize_job(db, job_log.id, models.ActionStatus.SUCCESS, items_processed)

    except ValueError as e:
        logger.warning(str(e))
    except Exception as e:
        logger.error(f"Media Processing Failed: {e}")
        db.rollback()
        if job_log:
            _finalize_job(db, job_log.id, models.ActionStatus.FAILED, items_processed, str(e))
    finally:
        db.close()


# ==========================================
# 3. ACADEMIC PROCESSING ORCHESTRATOR
# ==========================================

def process_pending_academic_task(user_id: int):
    """Background task: Deduplicates, AI Evaluation, Entity Matching for Academic data."""
    db = SessionLocal()
    job_log = None
    items_processed = 0

    try:
        job_log = _manage_job_lock(db, models.ActionType.ACADEMIC_PROCESSING, user_id)

        # ---------------------------------------------------------
        # PHASE 1: DEDUPLICATION (No scraper needed for SwePub)
        # ---------------------------------------------------------
        # MODIFICATION: Added quarantine guard.
        items_to_dedup = db.query(models.AcademicPublication).filter(
            models.AcademicPublication.is_duplicate.is_(None),
            models.AcademicPublication.has_processing_error == False
        ).all()

        if items_to_dedup:
            # TODO: from app.services.deduplicator import flag_academic_duplicates
            # flag_academic_duplicates(db, items_to_dedup)
            pass

        # ---------------------------------------------------------
        # PHASE 2: LLM EVALUATION
        # ---------------------------------------------------------
        # MODIFICATION: Changed trigger to `ai_recommendation` and added quarantine guard.
        items_to_eval = db.query(models.AcademicPublication).filter(
            models.AcademicPublication.is_duplicate == False,
            models.AcademicPublication.ai_recommendation.is_(None),
            models.AcademicPublication.has_processing_error == False
        ).all()

        if items_to_eval:
            # TODO: from app.services.llm import evaluate_academic
            # evaluate_academic(db, items_to_eval)
            items_processed += len(items_to_eval)

        # ---------------------------------------------------------
        # PHASE 3: ENTITY MATCHING
        # ---------------------------------------------------------
        # MODIFICATION: Changed to Post-Review trigger to save API calls.
        """
        # Placeholder for future implementation
        items_to_match = db.query(models.AcademicPublication).filter(
            models.AcademicPublication.is_reviewed == True,
            models.AcademicPublication.is_relevant == True,
            models.AcademicPublication.entities_matched.is_(None),
            models.AcademicPublication.has_processing_error == False
        ).all()

        if items_to_match:
            # from app.services.entity_matcher import link_academic_entities
            # link_academic_entities(db, items_to_match)
            pass
        """

        _finalize_job(db, job_log.id, models.ActionStatus.SUCCESS, items_processed)

    except ValueError as e:
        logger.warning(str(e))
    except Exception as e:
        logger.error(f"Academic Processing Failed: {e}")
        db.rollback()
        if job_log:
            _finalize_job(db, job_log.id, models.ActionStatus.FAILED, items_processed, str(e))
    finally:
        db.close()


# ==========================================
# 4. WORDPRESS PUSH ORCHESTRATORS
# ==========================================

def push_approved_media_task(user_id: int):
    """Background task: Finds evaluated & relevant MEDIA publications and pushes to WP."""
    db = SessionLocal()
    job_log = None
    items_pushed = 0

    try:
        job_log = _manage_job_lock(db, models.ActionType.MEDIA_PUBLISH, user_id)

        # MODIFICATION: Added `is_reviewed == True` as the absolute human-in-the-loop gatekeeper.
        # Added quarantine guard.
        media_to_push = db.query(models.MediaPublication).filter(
            models.MediaPublication.is_reviewed == True,
            models.MediaPublication.is_relevant == True,
            models.MediaPublication.wp_post_id.is_(None),
            models.MediaPublication.has_processing_error == False
        ).all()

        # TODO: from app.services.wordpress import push_media_to_wordpress
        # items_pushed = push_media_to_wordpress(db, media_to_push)

        _finalize_job(db, job_log.id, models.ActionStatus.SUCCESS, items_pushed)

    except ValueError as e:
        logger.warning(str(e))
    except Exception as e:
        logger.error(f"Media WordPress Push Failed: {e}")
        db.rollback()
        if job_log:
            _finalize_job(db, job_log.id, models.ActionStatus.FAILED, items_pushed, str(e))
    finally:
        db.close()


def push_approved_academic_task(user_id: int):
    """Background task: Finds evaluated & relevant ACADEMIC publications and pushes to WP."""
    db = SessionLocal()
    job_log = None
    items_pushed = 0

    try:
        job_log = _manage_job_lock(db, models.ActionType.ACADEMIC_PUBLISH, user_id)

        # MODIFICATION: Added `is_reviewed == True` and quarantine guard.
        academic_to_push = db.query(models.AcademicPublication).filter(
            models.AcademicPublication.is_reviewed == True,
            models.AcademicPublication.is_relevant == True,
            models.AcademicPublication.wp_post_id.is_(None),
            models.AcademicPublication.has_processing_error == False
        ).all()

        # TODO: from app.services.wordpress import push_academic_to_wordpress
        # items_pushed = push_academic_to_wordpress(db, academic_to_push)

        _finalize_job(db, job_log.id, models.ActionStatus.SUCCESS, items_pushed)

    except ValueError as e:
        logger.warning(str(e))
    except Exception as e:
        logger.error(f"Academic WordPress Push Failed: {e}")
        db.rollback()
        if job_log:
            _finalize_job(db, job_log.id, models.ActionStatus.FAILED, items_pushed, str(e))
    finally:
        db.close()
