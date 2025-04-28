from fastapi import FastAPI
from .database import engine, Base
from .config import settings
from .routers import user

# Create tables when in DEBUG mode
if settings.debug:
    Base.metadata.create_all(bind=engine)

app = FastAPI(debug=settings.debug)


# Test endpoint to confirm the server boots
@app.get("/ping")
def ping():
    return {"ping": "pong"}


app.include_router(user.router)
