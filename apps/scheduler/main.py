from celery import Celery
from datetime import timedelta
import asyncio
from apps.common import settings

# Create Celery app
app = Celery(
    'revmon',
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Celery configuration - optimized for cost efficiency
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    worker_prefetch_multiplier=1,  # Fetch one task at a time for better resource usage
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    result_expires=3600,  # Results expire after 1 hour
    task_acks_late=True,  # Acknowledge tasks after completion for reliability
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    broker_connection_retry_on_startup=True,
    broker_pool_limit=5,  # Limit broker connection pool (reduced from default 10)
    worker_disable_rate_limits=True,  # Disable rate limits for better performance
)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks."""
    from apps.storage import Repo
    from apps.common import get_logger

    logger = get_logger(__name__)

    # Hourly incremental crawl for all active hospitals
    sender.add_periodic_task(
        timedelta(hours=1),
        crawl_all_hospitals.s(),
        name='Hourly hospital review crawl'
    )

    # Sentiment analysis every 30 minutes
    sender.add_periodic_task(
        timedelta(minutes=30),
        analyze_sentiments.s(),
        name='Analyze new reviews'
    )

    # Notification processing every 5 minutes
    sender.add_periodic_task(
        timedelta(minutes=5),
        process_notifications.s(),
        name='Process flagged review notifications'
    )

    logger.info("Periodic tasks configured successfully")


@app.task(name='revmon.crawl_hospital')
def crawl_hospital(hospital_id: str, naver_place_url: str, is_initial: bool = False):
    """Crawl a single hospital's reviews."""
    from apps.crawler import crawl_hospital_task
    from apps.common import get_logger

    logger = get_logger(__name__)
    logger.info(f"Celery task: crawl_hospital for {hospital_id}")

    result = asyncio.run(crawl_hospital_task(hospital_id, naver_place_url, is_initial))
    return result


@app.task(name='revmon.crawl_all_hospitals')
def crawl_all_hospitals():
    """Crawl all active hospitals."""
    from apps.storage import Repo, get_db_session
    from apps.storage.models import Hospital
    from apps.common import get_logger

    logger = get_logger(__name__)
    logger.info("Starting crawl_all_hospitals task")

    with get_db_session() as session:
        hospitals = session.query(Hospital).filter(Hospital.status == 'active').all()

        for hospital in hospitals:
            logger.info(f"Queuing crawl for hospital: {hospital.id} - {hospital.name}")
            crawl_hospital.delay(str(hospital.id), hospital.naver_place_url, is_initial=False)

    logger.info(f"Queued crawl tasks for {len(hospitals)} hospitals")
    return {"queued": len(hospitals)}


@app.task(name='revmon.analyze_sentiments')
def analyze_sentiments():
    """Analyze sentiment for unanalyzed reviews."""
    from apps.sentiment.worker import run_sentiment_analysis
    from apps.common import get_logger

    logger = get_logger(__name__)
    logger.info("Starting analyze_sentiments task")

    result = asyncio.run(run_sentiment_analysis())
    return result


@app.task(name='revmon.process_notifications')
def process_notifications():
    """Process notifications for flagged reviews."""
    from apps.notify.worker import run_notification_worker
    from apps.common import get_logger

    logger = get_logger(__name__)
    logger.info("Starting process_notifications task")

    result = asyncio.run(run_notification_worker())
    return result


if __name__ == '__main__':
    app.start()
