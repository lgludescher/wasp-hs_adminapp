from fastapi import FastAPI
from fastapi import Request
from .database import engine, Base
from .config import settings
from .routers import user
from .logger import logger

# Create tables when in DEBUG mode
if settings.debug:
    Base.metadata.create_all(bind=engine)

app = FastAPI(debug=settings.debug)


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


# Test endpoint to confirm the server boots
@app.get("/ping")
def ping():
    return {"ping": "pong"}


app.include_router(user.router)
