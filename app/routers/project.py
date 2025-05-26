import logging
from fastapi import (
    APIRouter, Depends, HTTPException,
    Response, Query
)
from typing import List, Optional

from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
from ..models import EntityType

router = APIRouter(tags=["projects"])
logger = logging.getLogger(__name__)


# <editor-fold desc="ProjectCallType endpoints">
# --- Project Call Type endpoints ---

@router.get("/project-call-types/{pct_id}", response_model=schemas.ProjectCallTypeRead)
def read_project_call_type(
    pct_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    pct = crud.get_project_call_type(db, pct_id)
    if not pct:
        logger.warning(f"Project Call Type #{pct_id} not found")
        raise HTTPException(404, f"Project Call Type #{pct_id} not found")

    logger.info(f"{current_user.username} fetched project call type '{pct.type}'")

    return pct


@router.get("/project-call-types/", response_model=List[schemas.ProjectCallTypeRead])
def list_project_call_types(
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} listed project call types")
    return crud.list_project_call_types(db)


@router.post("/project-call-types/", response_model=schemas.ProjectCallTypeRead)
def create_project_call_type(
    pct_in: schemas.ProjectCallTypeCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} creating project call type {pct_in.type}")

    return crud.create_project_call_type(db, pct_in)


@router.put("/project-call-types/{pct_id}", response_model=schemas.ProjectCallTypeRead)
def update_project_call_type(
    pct_id: int,
    pct_in: schemas.ProjectCallTypeUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating project call type {pct_id} → {pct_in}")

    try:
        return crud.update_project_call_type(db, pct_id, pct_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/project-call-types/{pct_id}", status_code=204)
def delete_project_call_type(
    pct_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} deleting project call type {pct_id}")

    try:
        crud.delete_project_call_type(db, pct_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Project endpoints">
# --- Project endpoints ---

@router.get("/projects/{project_id}", response_model=schemas.ProjectRead)
def read_project(
    project_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    p = crud.get_project(db, project_id)
    if not p:
        logger.warning(f"Project #{project_id} not found")
        raise HTTPException(404, f"Project #{project_id} not found")

    logger.info(f"{current_user.username} fetched project [{p.id}] '{p.project_number}'")

    return p


@router.get("/projects/", response_model=List[schemas.ProjectRead])
def list_projects(
    call_type_id:   Optional[int] = Query(None, ge=1),
    title:          Optional[str] = Query(None),
    project_number: Optional[str] = Query(None),
    is_affiliated:  Optional[bool] = Query(None),
    is_extended:    Optional[bool] = Query(None),
    is_active:      Optional[bool] = Query(None),
    search:         Optional[str] = Query(None),
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listed projects (call_type_id={call_type_id}), (title={title}, "
                f"project_number={project_number}, is_affiliated={is_affiliated}, "
                f"is_extended={is_extended}, is_active={is_active} search={search!r})")
    return crud.list_projects(
        db,
        call_type_id=call_type_id,
        title=title,
        project_number=project_number,
        is_affiliated=is_affiliated,
        is_extended=is_extended,
        is_active=is_active,
        search=search
    )


@router.post("/projects/", response_model=schemas.ProjectRead)
def create_project(
    p_in: schemas.ProjectCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} creating project {p_in.project_number}")
    try:
        return crud.create_project(db, p_in)
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/projects/{project_id}", response_model=schemas.ProjectRead)
def update_project(
    project_id: int,
    p_in: schemas.ProjectUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating project {project_id} → {p_in}")

    try:
        return crud.update_project(db, project_id, p_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} deleting project {project_id}")

    try:
        crud.delete_project(db, project_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Project-related research output reports endpoints">
# — Research Output Reports —

@router.get("/projects/{pid}/research-output-reports/", response_model=list[schemas.ResearchOutputReportRead])
def project_research_output_reports(pid: int, db: Session = Depends(dependencies.get_db),
                                    current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} listed research output reports for project {pid}")
    return crud.list_research_output_reports(db, pid)


@router.post("/projects/{pid}/research-output-reports/", response_model=schemas.ResearchOutputReportRead)
def add_project_research_output_report(pid: int, ror_in: schemas.ResearchOutputReportCreate,
                                       db: Session = Depends(dependencies.get_db),
                                       current_user=Depends(dependencies.get_current_user)):
    if not crud.get_project(db, pid):
        logger.warning(f"Project #{pid} not found")
        raise HTTPException(404, f"Project #{pid} not found")
    logger.info(f"{current_user.username} adding research output report {ror_in.link} for project {pid}")
    return crud.add_research_output_report(db, pid, ror_in.link)


@router.put("/projects/{pid}/research-output-reports/{rorid}", response_model=schemas.ResearchOutputReportRead)
def update_project_research_output_report(
    pid: int, rorid: int,
    ror_in: schemas.ResearchOutputReportUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating research output report {rorid} → {ror_in} for project {pid}")

    try:
        return crud.update_research_output_report(db, rorid, ror_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/projects/{pid}/research-output-reports/{rorid}", status_code=204)
def del_project_research_output_report(pid: int, rorid: int,
                                       db: Session = Depends(dependencies.get_db),
                                       current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} removing research output report {rorid} for project {pid}")
    crud.remove_research_output_report(db, rorid)
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Project-related fields endpoints">
# — Academic Fields —

@router.get("/projects/{project_id}/fields/", response_model=list[schemas.FieldRead])
def list_project_fields(
    project_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing academic fields for project {project_id}")
    return crud.get_project_fields(db, project_id)


@router.post("/projects/{project_id}/fields/", response_model=schemas.FieldRead)
def add_project_field(
    project_id: int,
    link: schemas.ProjectFieldLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking field "
                f"{link.field_id} → project {project_id}")
    try:
        return crud.add_field_to_project(db, project_id, link.field_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/projects/{project_id}/fields/{field_id}", status_code=204)
def remove_project_field(
    project_id: int,
    field_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking field "
                f"{field_id} from project {project_id}")
    try:
        crud.remove_field_from_project(db, project_id, field_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="Project-related decision letters endpoints">
# — Decision Letters —

@router.get("/projects/{pid}/decision-letters/", response_model=list[schemas.DecisionLetterRead])
def project_decision_letters(pid: int, db: Session = Depends(dependencies.get_db),
                             current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} listed decision letters for project {pid}")
    return crud.list_decision_letters(db, EntityType.PROJECT, pid)


@router.post("/projects/{pid}/decision-letters/", response_model=schemas.DecisionLetterRead)
def add_project_decision_letter(pid: int, dl_in: schemas.DecisionLetterCreate,
                                db: Session = Depends(dependencies.get_db),
                                current_user=Depends(dependencies.get_current_user)):
    if not crud.get_project(db, pid):
        logger.warning(f"Project #{pid} not found")
        raise HTTPException(404, f"Project #{pid} not found")
    logger.info(f"{current_user.username} adding decision letter {dl_in.link} for project {pid}")
    return crud.add_decision_letter(db, EntityType.PROJECT, pid, dl_in.link)


@router.put("/projects/{pid}/decision-letters/{dlid}", response_model=schemas.DecisionLetterRead)
def update_project_decision_letter(
    pid: int, dlid: int,
    dl_in: schemas.DecisionLetterUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating decision letter {dlid} → {dl_in} for project {pid}")

    try:
        return crud.update_decision_letter(db, dlid, dl_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/projects/{pid}/decision-letters/{dlid}", status_code=204)
def del_course_decision_letter(pid: int, dlid: int,
                               db: Session = Depends(dependencies.get_db),
                               current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} removing decision letter {dlid} for project {pid}")
    crud.remove_decision_letter(db, dlid)
    return Response(status_code=204)


# </editor-fold>
