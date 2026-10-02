import ssl

from celery import Celery

from app.core.config import get_settings
from app.core.redis_runtime import parse_redis_target

settings = get_settings()
redis_target = parse_redis_target(settings.redis_url)

celery_app = Celery(
    "fincopilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_pool_limit=10,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    task_track_started=True,
    result_expires=settings.celery_result_expires_seconds,
    broker_transport_options={
        "visibility_timeout": settings.celery_visibility_timeout_seconds,
        "socket_connect_timeout": settings.redis_socket_connect_timeout_seconds,
        "socket_timeout": settings.redis_socket_timeout_seconds,
        "health_check_interval": settings.redis_health_check_interval_seconds,
    },
)

if redis_target.tls:
    ssl_options: dict[str, object] = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    if settings.redis_ssl_ca_file.strip():
        ssl_options["ssl_ca_certs"] = settings.redis_ssl_ca_file.strip()
    celery_app.conf.broker_use_ssl = ssl_options
    celery_app.conf.redis_backend_use_ssl = ssl_options

celery_app.conf.beat_schedule = {
    "sync-all-connections-hourly": {
        "task": "app.tasks.sync_tasks.sync_all_connections",
        "schedule": 60 * 60,
    },
    "generate-recurring-daily": {
        "task": "app.tasks.recurring_tasks.generate_all_recurring",
        "schedule": 60 * 60,
    },
    "apply-asset-growth-daily": {
        "task": "app.tasks.asset_tasks.apply_asset_growth_rules",
        "schedule": 60 * 60,
    },
    "refresh-market-prices-daily": {
        "task": "app.tasks.asset_tasks.refresh_market_prices",
        "schedule": 60 * 60 * 24,
    },
    "sync-fx-rates-daily": {
        "task": "app.tasks.fx_rate_tasks.sync_fx_rates",
        "schedule": 60 * 60 * 12,
    },
    "restamp-recurring-fx-daily": {
        "task": "app.tasks.fx_rate_tasks.restamp_recurring_fx",
        "schedule": 60 * 60 * 12,
    },
    "restamp-fallback-fx-daily": {
        "task": "app.tasks.fx_rate_tasks.restamp_fallback_fx",
        "schedule": 60 * 60 * 12,
    },
}

celery_app.conf.include = [
    "app.tasks.sync_tasks",
    "app.tasks.recurring_tasks",
    "app.tasks.asset_tasks",
    "app.tasks.fx_rate_tasks",
    "app.agents.tasks.ingest",
]


@celery_app.task(name="app.worker.health_probe")
def health_probe(nonce: str) -> dict[str, str | bool]:
    """Side-effect-free broker/worker/result-backend acceptance probe."""
    return {"ok": True, "nonce": nonce}
