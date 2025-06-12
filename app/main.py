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
                      person, researcher, phd_student, postdoc)
from .models import Role, RoleType
from .logger import logger

# Create tables when in DEBUG mode
if settings.debug:
    Base.metadata.create_all(bind=engine)

app = FastAPI(debug=settings.debug)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def seed_roles(db: Session):
    """Ensure the roles table contains exactly the members of RoleType."""
    existing = {r.role for r in db.query(Role).all()}
    for rt in RoleType:
        if rt not in existing:
            db.add(Role(role=rt))
    db.commit()


@app.on_event("startup")
def on_startup():
    # only if you want to run migrations here, else skip
    # Base.metadata.create_all(bind=engine)  # if you removed the DEBUG guard
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()


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
