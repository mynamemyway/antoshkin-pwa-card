# app/main.py

"""
FastAPI application entry point.

Initializes the FastAPI app, configures middleware,
and includes API routers.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import Base, engine
from app.api.routers import router

# Initialize database tables
# Creates all tables defined in models.py if they don't exist
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title="Antoshkin Loyalty Card",
    description="PWA for loyalty card management with SMS verification",
    version="0.1.0",
    debug=settings.DEBUG,
)

# Configure static files (CSS, JS, images, manifest)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
