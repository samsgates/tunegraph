from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from tunegraph.db.models import TrainingJob
from tunegraph.db.session import SessionLocal
from tunegraph.domain.enums import JobState
from tunegraph.logging import configure_logging
from tunegraph.config import get_settings
from tunegraph.ml.spec import TrainingSpecification
from tunegraph.ml.trainer import run_peft_training

logger = structlog.get_logger(__name__)


async def process_one() -> bool:
    settings = get_settings()
    async with SessionLocal() as session:
        job = (
            await session.execute(
                select(TrainingJob)
                .where(TrainingJob.state == JobState.QUEUED)
                .order_by(TrainingJob.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        if job is None:
            return False
        job.state = JobState.RUNNING
        job.started_at = datetime.now(UTC)
        await session.commit()
        job_id = job.id
        specification = TrainingSpecification.model_validate(job.specification)
        controlled_output = settings.artifact_root / "training" / job_id
        specification = specification.model_copy(
            update={"output_dir": str(controlled_output.resolve())}
        )

    try:
        result = await asyncio.to_thread(run_peft_training, specification)
    except Exception as exc:
        logger.exception("training_failed", job_id=job_id)
        async with SessionLocal() as session:
            job = await session.get(TrainingJob, job_id)
            if job:
                job.state = JobState.FAILED
                job.error_message = str(exc)[:10000]
                job.finished_at = datetime.now(UTC)
                await session.commit()
        return True

    async with SessionLocal() as session:
        job = await session.get(TrainingJob, job_id)
        if job:
            job.state = JobState.SUCCEEDED
            job.progress = 1.0
            job.artifact_uri = "file://" + result["output_dir"]
            job.finished_at = datetime.now(UTC)
            await session.commit()
    return True


async def run_forever(interval_seconds: float = 5.0) -> None:
    logger.info("worker_started")
    while True:
        processed = await process_one()
        if not processed:
            await asyncio.sleep(interval_seconds)


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
