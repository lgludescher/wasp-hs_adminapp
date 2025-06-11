import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session

from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
from ..models import EntityType

router = APIRouter(tags=["people"])
logger = logging.getLogger(__name__)


# <editor-fold desc="Role endpoints">
# --- Role endpoints ---

@router.get("/roles/{role_id}", response_model=schemas.RoleRead)
def read_role(
        role_id: int,
        current_user=Depends(dependencies.get_current_user),
        db: Session = Depends(dependencies.get_db)
):
    r = crud.get_role(db, role_id)
    if not r:
        logger.warning(f"Role {role_id} not found")
        raise HTTPException(404, f"Role #{role_id} not found")
    logger.info(f"{current_user.username} fetched role #{role_id}")
    return r


@router.get("/roles/", response_model=List[schemas.RoleRead])
def list_roles(
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} listed roles")
    return crud.list_roles(db)


# </editor-fold>

# <editor-fold desc="Person endpoints">
# --- Person endpoints ---

@router.get("/people/{person_id}", response_model=schemas.PersonRead)
def read_person(
    person_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    p = crud.get_person(db, person_id)
    if not p:
        logger.warning(f"Person #{person_id} not found")
        raise HTTPException(404, f"Person #{person_id} not found")
    logger.info(f"{current_user.username} fetched person #{person_id}")
    return p


@router.get("/people/", response_model=List[schemas.PersonRead])
def list_people(
    search: Optional[str] = Query(None, description="Substring search on first/last name or email"),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} listed people (search={search!r})")
    return crud.list_persons(db, search=search)


@router.post("/people/", response_model=schemas.PersonRead)
def create_person(
    person_in: schemas.PersonCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating person {person_in.first_name} {person_in.last_name}")
    try:
        return crud.create_person(db, person_in)
    except Exception as e:
        logger.warning(f"Failed to create person: {e}")
        raise HTTPException(400, str(e))


@router.put("/people/{person_id}", response_model=schemas.PersonRead)
def update_person(
    person_id: int,
    person_in: schemas.PersonUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating person #{person_id} → {person_in}")
    try:
        return crud.update_person(db, person_id, person_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/people/{person_id}", status_code=204)
def delete_person(
    person_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting person #{person_id}")
    try:
        crud.delete_person(db, person_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="PersonRole endpoints">
# --- PersonRole endpoints ---

@router.get("/person-roles/{person_role_id}", response_model=schemas.PersonRoleReadFull)
def read_person_role(
    person_role_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    pr = crud.get_person_role(db, person_role_id)
    if not pr:
        logger.warning(f"PersonRole #{person_role_id} not found")
        raise HTTPException(404, f"PersonRole #{person_role_id} not found")
    logger.info(f"{current_user.username} fetched person_role #{person_role_id}")
    return pr


@router.get("/person-roles/", response_model=List[schemas.PersonRoleReadFull])
def list_person_roles(
    person_id: Optional[int] = Query(None, ge=1),
    role_id:   Optional[int] = Query(None, ge=1),
    active:    Optional[bool] = Query(None),
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} listed person_roles (person_id={person_id}, role_id={role_id}, active={active})")
    return crud.list_person_roles(db, person_id=person_id, role_id=role_id, active=active)


@router.post("/person-roles/", response_model=schemas.PersonRoleReadFull)
def create_person_role(
    pr_in: schemas.PersonRoleCreate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} creating person_role {pr_in}")
    try:
        return crud.create_person_role(db, pr_in)
    except Exception as e:
        logger.warning(f"Failed to create person_role: {e}")
        raise HTTPException(400, str(e))


@router.put("/person-roles/{person_role_id}", response_model=schemas.PersonRoleReadFull)
def update_person_role(
    person_role_id: int,
    pr_in: schemas.PersonRoleUpdate,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} updating person_role #{person_role_id} → {pr_in}")
    try:
        return crud.update_person_role(db, person_role_id, pr_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/person-roles/{person_role_id}", status_code=204)
def delete_person_role(
    person_role_id: int,
    current_user=Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    logger.info(f"{current_user.username} deleting person_role #{person_role_id}")
    try:
        crud.delete_person_role(db, person_role_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="PersonRole-related institutions endpoints">
# — Institutions —

@router.get("/person-roles/{person_role_id}/institutions/",
            response_model=List[schemas.PersonRoleInstitutionRead])
def list_person_role_institutions(
    person_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing institutions for person role {person_role_id}")
    return crud.get_person_role_institutions(db, person_role_id)


@router.post("/person-roles/{person_role_id}/institutions/", response_model=schemas.PersonRoleInstitutionRead)
def add_person_role_institution(
    person_role_id: int,
    link: schemas.PersonRoleInstitutionLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking institution "
                f"{link.institution_id} → person role {person_role_id}")
    try:
        return crud.add_institution_to_person_role(db, person_role_id, link)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put("/person-roles/{person_role_id}/institutions/{institution_id}",
            response_model=schemas.PersonRoleInstitutionRead)
def update_person_role_institution(
    person_role_id: int,
    institution_id: int,
    link: schemas.PersonRoleInstitutionLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} updating person role-institution link: institution "
                f"{institution_id} for person role {person_role_id} → {link}")
    try:
        return crud.update_institution_person_role_link(db, person_role_id, institution_id, link)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/person-roles/{person_role_id}/institutions/{institution_id}", status_code=204)
def remove_person_role_institution(
    person_role_id: int,
    institution_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking institution "
                f"{institution_id} from person role {person_role_id}")
    try:
        crud.remove_institution_from_person_role(db, person_role_id, institution_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="PersonRole-related fields endpoints">
# — Academic Fields —

@router.get("/person-roles/{person_role_id}/fields/", response_model=List[schemas.FieldRead])
def list_person_role_fields(
    person_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing academic fields for person role {person_role_id}")
    return crud.get_person_role_fields(db, person_role_id)


@router.post("/person-roles/{person_role_id}/fields/", response_model=schemas.FieldRead)
def add_person_role_field(
    person_role_id: int,
    link: schemas.PersonRoleFieldLink,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} linking field "
                f"{link.field_id} → person role {person_role_id}")
    try:
        return crud.add_field_to_person_role(db, person_role_id, link.field_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete("/person-roles/{person_role_id}/fields/{field_id}", status_code=204)
def remove_person_role_field(
    person_role_id: int,
    field_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} unlinking field "
                f"{field_id} from person role {person_role_id}")
    try:
        crud.remove_field_from_person_role(db, person_role_id, field_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="PersonRole-related projects endpoints">
# — Projects —

@router.get("/person-roles/{person_role_id}/projects/", response_model=List[schemas.ProjectPersonRoleRead])
def list_person_role_projects(
    person_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user)
):
    logger.info(f"{current_user.username} listing projects for person role {person_role_id}")
    return crud.get_person_role_projects(db, person_role_id)


# </editor-fold>

# <editor-fold desc="PersonRole-related courses teaching endpoints">
# — Courses teaching —

@router.get("/person-roles/{person_role_id}/courses_teaching/", response_model=List[schemas.CourseRead])
def list_person_role_courses_teaching(
        person_role_id: int,
        is_active_term: Optional[bool] = Query(None),
        search: Optional[str] = Query(None, description="Substring search on title"),
        db: Session = Depends(dependencies.get_db),
        current_user=Depends(dependencies.get_current_user)
):
    logger.info(
        f"{current_user.username} listing courses taught by person role {person_role_id} "
        f"(is_active_term={is_active_term})"
        f"{' with search=' + search if search else ''}"
    )
    return crud.list_courses(db, teacher_role_id=person_role_id, is_active_term=is_active_term, search=search)


# </editor-fold>

# <editor-fold desc="Supervision relationships endpoints">

# ----------------------------------------------------------------
# Supervisors of a given student
# ----------------------------------------------------------------

@router.get(
    "/person-roles/{student_role_id}/supervisors/",
    response_model=List[schemas.SupervisionRead],
)
def list_student_supervisors(
    student_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} listing supervisors for student role {student_role_id}")
    return crud.list_supervisions(db, student_role_id=student_role_id)


@router.post(
    "/person-roles/{student_role_id}/supervisors/",
    response_model=schemas.SupervisionRead,
)
def add_student_supervisor(
    student_role_id: int,
    data: schemas.SupervisionCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    # force the path param
    data.student_role_id = student_role_id

    logger.info(f"{current_user.username} linking supervisor "
                f"{data.supervisor_role_id} → student {student_role_id}")
    try:
        return crud.create_supervision(db, data)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put(
    "/person-roles/{student_role_id}/supervisors/{supervision_id}",
    response_model=schemas.SupervisionRead,
)
def update_student_supervisor(
    student_role_id: int,
    supervision_id: int,
    data: schemas.SupervisionUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating supervision #{supervision_id} "
                f"for student {student_role_id} → {data}")
    try:
        return crud.update_supervision(db, supervision_id, data)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete(
    "/person-roles/{student_role_id}/supervisors/{supervision_id}",
    status_code=204,
)
def remove_student_supervisor(
    student_role_id: int,
    supervision_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} unlinking supervision #{supervision_id} "
                f"from student {student_role_id}")
    try:
        crud.delete_supervision(db, supervision_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# -----------------------------------------------------------------
# Students supervised by a given role (mirror endpoints for students)
# -----------------------------------------------------------------

@router.get(
    "/person-roles/{supervisor_role_id}/students/",
    response_model=List[schemas.SupervisionRead],
)
def list_supervisor_students(
    supervisor_role_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} listing students for supervisor role {supervisor_role_id}")
    return crud.list_supervisions(db, supervisor_role_id=supervisor_role_id)


@router.post(
    "/person-roles/{supervisor_role_id}/students/",
    response_model=schemas.SupervisionRead,
)
def add_student_for_supervisor(
    supervisor_role_id: int,
    data: schemas.SupervisionCreate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    # force the path param
    data.supervisor_role_id = supervisor_role_id

    logger.info(f"{current_user.username} linking student "
                f"{data.student_role_id} → supervisor {supervisor_role_id}")
    try:
        return crud.create_supervision(db, data)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.put(
    "/person-roles/{supervisor_role_id}/students/{supervision_id}",
    response_model=schemas.SupervisionRead,
)
def update_student_for_supervisor(
    supervisor_role_id: int,
    supervision_id: int,
    data: schemas.SupervisionUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating supervision #{supervision_id} "
                f"for supervisor {supervisor_role_id} → {data}")
    try:
        return crud.update_supervision(db, supervision_id, data)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(400, str(e))


@router.delete(
    "/person-roles/{supervisor_role_id}/students/{supervision_id}",
    status_code=204,
)
def remove_student_for_supervisor(
    supervisor_role_id: int,
    supervision_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} unlinking supervision #{supervision_id} "
                f"from supervisor {supervisor_role_id}")
    try:
        crud.delete_supervision(db, supervision_id)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>

# <editor-fold desc="PersonRole-related decision letters endpoints">
# — Decision Letters —

@router.get("/person-roles/{person_role_id}/decision-letters/", response_model=List[schemas.DecisionLetterRead])
def person_role_decision_letters(person_role_id: int, db: Session = Depends(dependencies.get_db),
                                 current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} listed decision letters for person role {person_role_id}")
    return crud.list_decision_letters(db, EntityType.PERSON_ROLE, person_role_id)


@router.post("/person-roles/{person_role_id}/decision-letters/", response_model=schemas.DecisionLetterRead)
def add_person_role_decision_letter(person_role_id: int, dl_in: schemas.DecisionLetterCreate,
                                    db: Session = Depends(dependencies.get_db),
                                    current_user=Depends(dependencies.get_current_user)):
    if not crud.get_person_role(db, person_role_id):
        logger.warning(f"Person role #{person_role_id} not found")
        raise HTTPException(404, f"Person role #{person_role_id} not found")
    logger.info(f"{current_user.username} adding decision letter {dl_in.link} for person role {person_role_id}")
    return crud.add_decision_letter(db, EntityType.PERSON_ROLE, person_role_id, dl_in.link)


@router.put("/person-roles/{person_role_id}/decision-letters/{dlid}", response_model=schemas.DecisionLetterRead)
def update_person_role_decision_letter(
    person_role_id: int, dlid: int,
    dl_in: schemas.DecisionLetterUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_user),
):
    logger.info(f"{current_user.username} updating decision letter {dlid} → {dl_in} for person role {person_role_id}")

    try:
        return crud.update_decision_letter(db, dlid, dl_in)
    except EntityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(404, str(e))


@router.delete("/person-roles/{person_role_id}/decision-letters/{dlid}", status_code=204)
def del_person_role_decision_letter(person_role_id: int, dlid: int,
                                    db: Session = Depends(dependencies.get_db),
                                    current_user=Depends(dependencies.get_current_user)):
    logger.info(f"{current_user.username} removing decision letter {dlid} for person role {person_role_id}")
    crud.remove_decision_letter(db, dlid)
    return Response(status_code=204)


# </editor-fold>
