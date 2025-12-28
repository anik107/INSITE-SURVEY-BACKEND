"""API v1 router aggregator."""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.templates import router as templates_router
from app.api.v1.surveys import router as surveys_router
from app.api.v1.responses import router as responses_router
from app.api.v1.public import router as public_router

router = APIRouter(prefix="/api/v1")

# Include all routers
router.include_router(auth_router)
router.include_router(templates_router)
router.include_router(surveys_router)
router.include_router(responses_router)
router.include_router(public_router)
