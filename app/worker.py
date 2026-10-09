"""
Background job worker for certificate generation.

Design decision — Python threading:
    We use Python's built-in `threading` module to run the bulk generation
    asynchronously.  This means:
    - The API returns immediately with a job ID (HTTP 202 Accepted).
    - Generation runs in a daemon thread inside the same process.
    - No external infrastructure (Redis, RabbitMQ, etc.) is required.

    Trade-offs vs. a task queue (Celery + Redis):
    - Simpler setup / zero extra services → better for this assignment.
    - Not horizontally scalable (only one worker per process).
    - If the process crashes mid-job, pending certificates stay "pending"
      and won't be retried automatically.
    - For a production system with hundreds of thousands of recipients a
      proper task queue would be the right choice; that reasoning is
      documented in the README.

    Within a job, certificates are processed sequentially.  A failure while
    generating one certificate is caught, logged, and stored — it does NOT
    abort the rest of the job.
"""

import logging
import threading

from flask import Flask

from .certificate_generator import generate_certificate
from .extensions import db
from .models import Certificate, Job

logger = logging.getLogger(__name__)


def _process_job(app: Flask, job_id: str) -> None:
    """
    Worker function executed in a background thread.

    Steps:
        1. Mark the job as "processing".
        2. Iterate over every pending certificate in the job.
        3. Generate the PDF; on success mark the certificate "success",
           on any exception mark it "failed" with the error message.
        4. After all certificates are processed, set the final job status:
           - "completed" if every certificate succeeded.
           - "failed"    if every certificate failed.
           - "completed" with partial failures otherwise (the client can
             inspect individual certificate statuses to see which failed).
    """
    with app.app_context():
        job: Job | None = db.session.get(Job, job_id)
        if job is None:
            logger.error("process_job: job %s not found", job_id)
            return

        # Transition to processing
        job.status = "processing"
        db.session.commit()

        certificates: list[Certificate] = (
            Certificate.query.filter_by(job_id=job_id, status="pending").all()
        )

        output_dir = app.config["CERTIFICATES_DIR"]

        for cert in certificates:
            try:
                file_path = generate_certificate(
                    output_dir=output_dir,
                    certificate_id=cert.id,
                    recipient_name=cert.recipient_name,
                    recipient_email=cert.recipient_email,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                )
                cert.status = "success"
                cert.file_path = file_path
                logger.info("Certificate %s generated: %s", cert.id, file_path)
            except Exception as exc:  # noqa: BLE001
                cert.status = "failed"
                cert.error_message = str(exc)
                logger.exception("Failed to generate certificate %s", cert.id)

            # Commit after every certificate so the client can track
            # real-time progress via the status endpoint.
            db.session.commit()

        # Determine final job status
        total = len(certificates)
        failed_count = sum(1 for c in certificates if c.status == "failed")

        if total == 0 or failed_count == total:
            job.status = "failed"
        else:
            job.status = "completed"

        db.session.commit()
        logger.info(
            "Job %s finished: %d total, %d failed", job_id, total, failed_count
        )


def start_job_worker(app: Flask, job_id: str) -> None:
    """
    Spawn a daemon thread to process *job_id* in the background.

    The thread is a daemon so it won't prevent the interpreter from
    exiting if the main process shuts down.
    """
    thread = threading.Thread(
        target=_process_job,
        args=(app, job_id),
        name=f"cert-worker-{job_id}",
        daemon=True,
    )
    thread.start()
    logger.info("Started background worker thread for job %s", job_id)
