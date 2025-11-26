from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi import Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import http_exception_handler
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .config import settings
from .dependencies import get_current_user
from .routers import (user, institution, domain, grad_school_activity, course, project,
                      person, researcher, phd_student, postdoc, report)
from .models import Role, RoleType
from .logger import logger

# Create tables when in DEBUG mode
if settings.debug:
    Base.metadata.create_all(bind=engine)


# --- HELPER FUNCTIONS ---

def seed_roles(db: Session):
    """Ensure the roles table contains exactly the members of RoleType."""
    existing = {r.role for r in db.query(Role).all()}
    for rt in RoleType:
        if rt not in existing:
            db.add(Role(role=rt))
    db.commit()


# --- LIFESPAN CONTEXT MANAGER (Replaces on_event) ---

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # 1. Startup Logic
    # It is safe to run synchronous DB code here; it only blocks once during boot.
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()

    yield  # Application runs here

    # 2. Shutdown Logic (Optional - currently empty)
    pass


# --- APP INITIALIZATION ---

app = FastAPI(debug=settings.debug, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# @app.on_event("startup")
# def on_startup():
#     # only if you want to run migrations here, else skip
#     # Base.metadata.create_all(bind=engine)  # if you removed the DEBUG guard
#     db = SessionLocal()
#     try:
#         seed_roles(db)
#     finally:
#         db.close()


# Log every request and unhandled exception
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url}")
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"Error while handling {request.method} {request.url}")
        raise
    logger.info(f"← {request.method} {request.url} — {response.status_code}")
    return response


@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code in (401, 403):
        return templates.TemplateResponse(
            f"{exc.status_code}.html",
            {"request": request, "error_message": exc.detail},
            status_code=exc.status_code
        )
    # fallback to default
    return await http_exception_handler(request, exc)


# Test endpoint to confirm the server boots
@app.get("/ping")
def ping():
    return {"ping": "pong"}


@app.get("/config")
def get_config(current_user=Depends(get_current_user)):
    return {"debug": settings.debug}


@app.get("/", response_class=HTMLResponse, summary="Home page (protected)")
async def read_home(
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Renders the home dashboard. Authentication is handled by Apache or X-Dev-User header;
    get_current_user will 401/403 if invalid or not provisioned.
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.get("/manage-users", response_class=HTMLResponse, summary="Manage Users (Admin only)")
async def manage_users_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    # Only admins may access
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="User not provisioned")
    return templates.TemplateResponse(
        "manage_users.html",
        {"request": request}
    )


@app.get("/manage-academic-domains", response_class=HTMLResponse, summary="Manage Academic Domains")
async def manage_academic_domains_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    # All authenticated users may view
    return templates.TemplateResponse(
        "manage_academic_domains.html",
        {"request": request}
    )


@app.get("/manage-institutions", response_class=HTMLResponse, summary="Manage Institutions")
async def manage_institutions_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_institutions.html",
        {"request": request}
    )


@app.get("/manage-grad-school-activities/types", response_class=HTMLResponse,
         summary="Manage Grad School Activity Types")
async def manage_grad_school_activity_types_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_grad_school_activity_types.html",
        {"request": request}
    )


@app.get("/manage-courses/terms", response_class=HTMLResponse, summary="Manage Course Terms")
async def manage_course_terms_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_course_terms.html",
        {"request": request}
    )


@app.get("/manage-projects/call-types", response_class=HTMLResponse, summary="Manage Project Call Types")
async def manage_project_call_types_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_project_call_types.html",
        {"request": request}
    )


@app.get("/manage-researchers/titles", response_class=HTMLResponse, summary="Manage Researcher Titles")
async def manage_researcher_titles_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_researcher_titles.html",
        {"request": request}
    )


@app.get("/manage-grad-school-activities", response_class=HTMLResponse,
         summary="Manage Grad School Activities")
async def manage_grad_school_activities_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_grad_school_activities.html",
        {"request": request}
    )


@app.get("/manage-courses", response_class=HTMLResponse)
async def manage_courses_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_courses.html",
        {"request": request}
    )


@app.get("/manage-projects", response_class=HTMLResponse)
async def manage_projects_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_projects.html",
        {"request": request}
    )


@app.get("/manage-people/", response_class=HTMLResponse)
async def manage_people_page(
    request: Request,
    current_user=Depends(get_current_user),
):
    return templates.TemplateResponse(
        "manage_people.html",
        {"request": request}
    )


@app.get("/manage-researchers", response_class=HTMLResponse)
async def manage_researchers_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_researchers.html",
        {"request": request}
    )


@app.get("/manage-phd-students", response_class=HTMLResponse)
async def manage_phd_students_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_phd_students.html",
        {"request": request}
    )


@app.get("/manage-postdocs", response_class=HTMLResponse)
async def manage_postdocs_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_postdocs.html",
        {"request": request}
    )


@app.get("/manage-researchers/{researcher_id}", response_class=HTMLResponse)
async def manage_researcher_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_researcher.html",
        {"request": request}
    )


@app.get("/manage-phd-students/{phd_student_id}", response_class=HTMLResponse)
async def manage_phd_student_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_phd_student.html",
        {"request": request}
    )


@app.get("/manage-postdocs/{postdoc_id}", response_class=HTMLResponse)
async def manage_postdoc_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_postdoc.html",
        {"request": request}
    )


@app.get("/manage-projects/{project_id}", response_class=HTMLResponse)
async def manage_project_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_project.html",
        {"request": request}
    )


@app.get("/manage-courses/{course_id}", response_class=HTMLResponse)
async def manage_course_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_course.html",
        {"request": request}
    )


@app.get("/manage-grad-school-activities/{grad_school_activity_id}", response_class=HTMLResponse)
async def manage_grad_school_activity_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "manage_grad_school_activity.html",
        {"request": request}
    )


@app.get("/reports/supervisors-report/", response_class=HTMLResponse)
async def report_supervisors_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "report_supervisors.html",
        {"request": request}
    )


@app.get("/reports/project-leaders-report/", response_class=HTMLResponse)
async def report_project_leaders_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "report_project_leaders.html",
        {"request": request}
    )


@app.get("/reports/semester-abroad-report/", response_class=HTMLResponse)
async def report_semester_abroad_page(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "report_semester_abroad.html",
        {"request": request}
    )


app.include_router(user.router)
app.include_router(institution.router)
app.include_router(domain.router)
app.include_router(grad_school_activity.router)
app.include_router(course.router)
app.include_router(project.router)
app.include_router(person.router)
app.include_router(researcher.router)
app.include_router(phd_student.router)
app.include_router(postdoc.router)
app.include_router(report.router)
