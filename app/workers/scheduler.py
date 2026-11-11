from typing import Any

from arq.connections import RedisSettings

from app.core.config import settings


async def health_ping_task(_ctx: dict[str, Any]) -> str:
    """Baseline background task for ARQ worker verification in Railway."""
    return "pong"


class WorkerSettings:
    """ARQ Worker configuration for Railway background service."""

    functions = [health_ping_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300

