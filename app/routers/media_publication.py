import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Query, UploadFile, File

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies, models
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
    is_relevant:     Optional[bool] = Query(None),
    is_reviewed:     Optional[bool] = Query(None),
    is_pushed_to_wp: Optional[bool] = Query(None),
    search:          Optional[str] = Query(None, description="Substring search on title or source"),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed media publications (platform={platform}, "
                f"is_relevant={is_relevant}, is_reviewed={is_reviewed}, "
                f"is_pushed_to_wp={is_pushed_to_wp}, search={search!r})")
    return crud.list_media_publications(
        db,
        platform=platform,
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

@router.post("/media-publications/actions/upload")
def upload_media_file(
    file: UploadFile = File(...),
    platform: models.MediaPlatform = Query(...),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    """Placeholder: Parse CSV/Excel from Retriever or Factiva."""
    logger.info(f"{current_user.username} triggered file upload for platform {platform}")
    return {"status": "Not implemented", "filename": file.filename, "platform": platform}


@router.post("/media-publications/actions/process-pending")
def process_pending_media(
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    """Placeholder: Trigger Azure OpenAI to evaluate is_relevant for unreviewed items."""
    logger.info(f"{current_user.username} triggered LLM processing for pending media")
    return {"status": "Not implemented", "message": "Will process unreviewed articles"}


@router.post("/media-publications/actions/push-to-wp")
def push_approved_media_to_wp(
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    """Placeholder: Push approved articles to WordPress."""
    logger.info(f"{current_user.username} triggered WP push for approved media")
    return {"status": "Not implemented", "message": "Will push relevant items to WP"}

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
