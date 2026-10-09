import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def _utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Job(db.Model):
    """
    Represents a bulk certificate generation job.

    A job is created when a client submits a list of recipients.
    It tracks the overall progress and status of the bulk operation.

    Status transitions:
        pending -> processing -> completed | failed
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Overall job status: pending | processing | completed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # Relationship: one job has many certificate records
    certificates: Mapped[List["Certificate"]] = relationship(
        "Certificate", back_populates="job", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        event_name: str,
        issuer_name: str,
        status: str = "pending",
        id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        if id is not None:
            self.id = id
        self.event_name = event_name
        self.issuer_name = issuer_name
        self.status = status

    @property
    def total(self) -> int:
        return len(self.certificates)

    @property
    def succeeded(self) -> int:
        return sum(1 for c in self.certificates if c.status == "success")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.certificates if c.status == "failed")

    @property
    def pending(self) -> int:
        return sum(1 for c in self.certificates if c.status == "pending")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_name": self.event_name,
            "issuer_name": self.issuer_name,
            "status": self.status,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "pending": self.pending,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Certificate(db.Model):
    """
    Represents a single certificate within a job.

    Each recipient in a job gets one Certificate record.
    Its status tracks whether its PDF was generated successfully.

    Status values:
        pending   - waiting to be processed
        success   - PDF generated and saved
        failed    - generation failed; error_message contains the reason
    """

    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=False, index=True
    )

    # Recipient information
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Generation result
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    file_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )  # path to generated PDF
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # error info if failed

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # Back-reference to parent job
    job: Mapped["Job"] = relationship("Job", back_populates="certificates")

    def __init__(
        self,
        job_id: str,
        recipient_name: str,
        recipient_email: str,
        status: str = "pending",
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
        id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        if id is not None:
            self.id = id
        self.job_id = job_id
        self.recipient_name = recipient_name
        self.recipient_email = recipient_email
        self.status = status
        self.file_path = file_path
        self.error_message = error_message

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
