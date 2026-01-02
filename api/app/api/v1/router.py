"""
API v1 main router.
Aggregates all v1 route modules.
"""
from fastapi import APIRouter

from app.api.v1.routes import hello_routes, claude_routes

# Create the main v1 router
api_router = APIRouter()

# Include all route modules
api_router.include_router(hello_routes.router)
api_router.include_router(claude_routes.router)
