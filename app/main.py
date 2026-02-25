# app/main.py

"""
FastAPI application entry point.

Initializes the FastAPI app, configures middleware,
and includes API routers.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings

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


@app.get("/")
async def root(request):
    """
    Root endpoint - serves the main registration page.
    
    Args:
        request: FastAPI request object (required for templates)
    
    Returns:
        Rendered HTML template for the registration page
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        Simple status response
    """
    return {"status": "ok", "debug": settings.DEBUG}
