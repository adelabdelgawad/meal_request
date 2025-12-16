import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.hris_database import get_hris_session
from api.deps import get_session
from settings import settings
from utils.replicate_hris import replicate

# === Logging Setup ===
# Configure console logging for the replication service
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
logger.info("HRIS Replication Service started")

# === Main Task ===


async def main():
    """Main replication task that syncs HRIS data to local database."""
    hris_session = None
    app_session = None

    try:
        # Get database sessions using async context managers
        hris_session_gen = get_hris_session()
        hris_session = await hris_session_gen.__anext__()

        app_session_gen = get_session()
        app_session = await app_session_gen.__anext__()

        # Run replication
        await replicate(hris_session, app_session)

        # Commit changes
        await app_session.commit()

        logger.info("Replication task completed successfully.")

    except Exception as e:
        # Log errors and rollback on failure
        logger.exception(f"Error during replication: {e}")
        if app_session:
            await app_session.rollback()
        raise
    finally:
        # Clean up sessions
        if hris_session:
            await hris_session.close()
        if app_session:
            await app_session.close()


# === Scheduler Setup ===


async def scheduler_loop():
    """Run replication immediately, then schedule hourly runs and attendance sync."""
    # Run immediately on startup
    logger.info("Running initial replication on startup...")
    await main()

    # Schedule hourly runs for HRIS replication
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        main,
        "interval",
        hours=1,
        id="hris_replication",
        name="HRIS Data Replication",
        replace_existing=True,
    )
    logger.info("Scheduled HRIS replication job (interval: 1 hour)")

    scheduler.start()
    logger.info("Scheduler started.")

    # Keep the scheduler running
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(scheduler_loop())
