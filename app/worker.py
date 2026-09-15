import asyncio
import logging
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings

logger = logging.getLogger(__name__)
PRODUCTS = ("consumer_loan", "mortgage")


async def run_scheduled_monitoring() -> None:
    for product in PRODUCTS:
        logger.info(
            "scheduled tariff run awaiting pipeline implementation",
            extra={"product": product, "trigger": "schedule"},
        )


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    scheduler = AsyncIOScheduler(timezone=settings.schedule_timezone)
    scheduler.add_job(
        run_scheduled_monitoring,
        trigger="cron",
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        id="daily-ameria-tariff-monitoring",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
