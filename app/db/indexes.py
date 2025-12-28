"""MongoDB index creation for performance and constraints."""
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all required indexes on startup."""

    logger.info("Creating database indexes...")

    # Users collection
    await db.users.create_indexes([
        IndexModel([("username", ASCENDING)], unique=True),
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("role", ASCENDING), ("status", ASCENDING)]),
        IndexModel([("attraction_id", ASCENDING)]),
    ])
    logger.info("Created indexes for 'users' collection")

    # Sessions collection (for refresh tokens)
    await db.sessions.create_indexes([
        IndexModel([("token_jti", ASCENDING)], unique=True),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),  # TTL index
    ])
    logger.info("Created indexes for 'sessions' collection")

    # Templates collection
    # BR-TPL-001: Only one published template at a time
    await db.templates.create_indexes([
        IndexModel([("status", ASCENDING)]),
        IndexModel(
            [("status", ASCENDING)],
            unique=True,
            partialFilterExpression={"status": "published"},
            name="unique_published_template",
        ),
        IndexModel([("created_by", ASCENDING)]),
        IndexModel([("updated_at", DESCENDING)]),
    ])
    logger.info("Created indexes for 'templates' collection")

    # Surveys collection
    await db.surveys.create_indexes([
        IndexModel([("share_id", ASCENDING)], unique=True),
        IndexModel([("template_id", ASCENDING)]),
        IndexModel([("attraction_id", ASCENDING)]),
        IndexModel([("attraction_id", ASCENDING), ("status", ASCENDING)]),
        # BR-SRV-001: Only one published survey per attraction
        IndexModel(
            [("attraction_id", ASCENDING), ("status", ASCENDING)],
            unique=True,
            partialFilterExpression={"status": "published"},
            name="unique_published_survey_per_attraction",
        ),
        IndexModel([("updated_at", DESCENDING)]),
    ])
    logger.info("Created indexes for 'surveys' collection")

    # Survey responses collection
    await db.survey_responses.create_indexes([
        IndexModel([("survey_id", ASCENDING), ("submitted_at", DESCENDING)]),
        IndexModel([("attraction_id", ASCENDING), ("submitted_at", DESCENDING)]),
        IndexModel([("template_id", ASCENDING)]),
        IndexModel([("duplicate_fingerprint", ASCENDING), ("submitted_at", ASCENDING)]),
        IndexModel([("submitted_at", DESCENDING)]),
    ])
    logger.info("Created indexes for 'survey_responses' collection")

    # Attractions collection
    await db.attractions.create_indexes([
        IndexModel([("admin_id", ASCENDING)], unique=True, sparse=True),
        IndexModel([("subscription_status", ASCENDING)]),
    ])
    logger.info("Created indexes for 'attractions' collection")

    # Section requests collection
    await db.section_requests.create_indexes([
        IndexModel([("attraction_id", ASCENDING)]),
        IndexModel([("admin_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])
    logger.info("Created indexes for 'section_requests' collection")

    # Subscription transactions collection
    await db.subscription_transactions.create_indexes([
        IndexModel([("attraction_id", ASCENDING), ("payment_date", DESCENDING)]),
        IndexModel([("admin_id", ASCENDING)]),
        IndexModel([("reference", ASCENDING)], unique=True),
    ])
    logger.info("Created indexes for 'subscription_transactions' collection")

    logger.info("All database indexes created successfully")
