"""Entry point for the FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.mongo import connect_to_mongo, close_mongo_connection, get_database
from app.db.indexes import create_indexes
from app.api.v1.router import router as api_v1_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting up application...")
    await connect_to_mongo()

    # Create indexes
    try:
        db = get_database()
        await create_indexes(db)
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    description="InSite Survey Management Portal API",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging."""
    print(f"========== VALIDATION ERROR ==========")
    print(f"Errors: {exc.errors()}")
    print(f"Body: {exc.body}")
    print(f"======================================")
    logger.error(f"Validation error: {exc.errors()}")
    logger.error(f"Request body: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application-specific exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": None,
        },
    )


# Include API router
app.include_router(api_v1_router)


# System endpoints
@app.get("/health", tags=["System"])
async def healthcheck() -> dict[str, str]:
    """Simple health endpoint used for uptime monitoring."""
    return {"status": "ok"}


@app.get("/metadata/collections", tags=["System"])
async def list_collections() -> dict[str, list[str]]:
    """Describe the key MongoDB collections managed by this service."""
    return {
        "collections": [
            "users",
            "sessions",
            "attractions",
            "templates",
            "surveys",
            "survey_responses",
            "section_requests",
            "subscription_transactions",
        ]
    }
