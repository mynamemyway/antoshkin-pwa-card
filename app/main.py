# app/main.py

"""
FastAPI application entry point.

Initializes the FastAPI app, configures middleware,
and includes API routers.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse  # Добавлено для работы с файлами

from app.config import settings
from app.database import Base, sync_engine
from app.api.routers import router
from app.middleware.auth import SessionAuthMiddleware
import os


# Initialize database tables
# Creates all tables defined in models.py if they don't exist
Base.metadata.create_all(bind=sync_engine)

# Initialize FastAPI application
app = FastAPI(
    title="Antoshkin Loyalty Card",
    description="PWA for loyalty card management with SMS verification",
    version="0.1.0",
    debug=settings.DEBUG,
)

# Add authentication middleware
# Runs on every request, injects current_user into request.state
app.add_middleware(SessionAuthMiddleware)

# Configure static files (CSS, JS, images, manifest)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Получаем путь к папке, где лежит этот файл (main.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(BASE_DIR, "favicon.ico"))

@app.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch():
    # Если в корне лежит icon-180.png, укажи его имя. 
    # Если переименовал в apple-touch-icon.png, оставь так:
    return FileResponse(os.path.join(BASE_DIR, "apple-touch-icon.png"))

@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def apple_touch_precomposed():
    return FileResponse(os.path.join(BASE_DIR, "apple-touch-icon-precomposed.png"))

@app.get("/robots.txt", include_in_schema=False)
async def robots():
    return FileResponse(os.path.join(BASE_DIR, "robots.txt"))

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")


@app.middleware("http")
async def add_templates_to_request(request: Request, call_next):
    """
    Middleware to add templates to request state.

    Makes templates available in endpoints via request.state.templates
    """
    request.state.templates = templates
    response = await call_next(request)
    return response


# Include API router
app.include_router(router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        Simple status response
    """
    return {"status": "ok", "debug": settings.DEBUG}