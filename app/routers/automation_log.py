import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies, models

router = APIRouter(tags=["automation_logs"])
logger = logging.getLogger(__name__)


# <editor-fold desc="Automation Log endpoints">
# --- Automation Log endpoints ---

@router.get("/automation-logs/latest", response_model=schemas.AutomationLogRead)
def read_latest_automation_log(
        action_type: models.ActionType = Query(..., description="The specific action type to fetch the latest log for"),
        status: Optional[models.ActionStatus] = Query(None, description="Optionally filter by a specific status"),
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} fetched latest automation log (action_type={action_type}, status={status})")

    log = crud.get_latest_automation_log(db, action_type=action_type, status=status)
    if not log:
        logger.warning(f"No automation log found for action_type '{action_type}'")
        raise HTTPException(404, f"No automation log found for action_type '{action_type}'")

    return log


@router.get("/automation-logs/{log_id}", response_model=schemas.AutomationLogRead)
def read_automation_log(
        log_id: int,
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    log = crud.get_automation_log(db, log_id)
    if not log:
        logger.warning(f"Automation Log #{log_id} not found")
        raise HTTPException(404, f"Automation Log #{log_id} not found")

    logger.info(f"{current_user.username} fetched automation log #{log_id}")
    return log


@router.get("/automation-logs/", response_model=List[schemas.AutomationLogRead])
def list_automation_logs(
        action_type: Optional[models.ActionType] = Query(None),
        trigger_source: Optional[models.TriggerSource] = Query(None),
        status: Optional[models.ActionStatus] = Query(None),
        user_id: Optional[int] = Query(None, ge=1),
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed automation logs (action_type={action_type}, "
                f"trigger_source={trigger_source}, status={status}, user_id={user_id})")

    return crud.list_automation_logs(
        db,
        action_type=action_type,
        trigger_source=trigger_source,
        status=status,
        user_id=user_id
    )

# </editor-fold>
