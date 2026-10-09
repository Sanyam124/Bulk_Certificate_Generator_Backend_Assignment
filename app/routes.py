"""
API routes (Flask Blueprint).

All endpoints are registered under the /api prefix (see create_app).

Endpoints
---------
POST   /api/jobs                    Create a bulk certificate generation job
GET    /api/jobs/<job_id>           Get job status and progress
GET    /api/jobs/<job_id>/certificates          List all certificates in a job
GET    /api/jobs/<job_id>/certificates/<cert_id>  Get a single certificate detail
GET    /api/jobs/<job_id>/certificates/<cert_id>/download  Download the PDF
"""

import os
from marshmallow import ValidationError

from flask import Blueprint, current_app, jsonify, request, send_file

from .extensions import db
from .models import Certificate, Job
from .schemas import JobCreateSchema
from .worker import start_job_worker

jobs_bp = Blueprint("jobs", __name__)

_job_schema = JobCreateSchema()


# ── Job endpoints ─────────────────────────────────────────────────────────────


@jobs_bp.post("/jobs")
def create_job():
    """
    Create a bulk certificate generation job.

    Request body (JSON)
    -------------------
    {
        "event_name": "Python Bootcamp 2025",
        "issuer_name": "Acme Academy",
        "recipients": [
            {"recipient_name": "Alice Smith", "recipient_email": "alice@example.com"},
            ...
        ]
    }

    Responses
    ---------
    202  Job accepted and queued for processing.
    400  Validation error — body contains a detailed error map.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # Validate request
    try:
        data = _job_schema.load(body)
    except ValidationError as exc:
        return jsonify({"error": "Validation failed.", "details": exc.messages}), 400

    # Create the Job row
    job = Job(event_name=data["event_name"], issuer_name=data["issuer_name"])
    db.session.add(job)
    db.session.flush()  # get job.id before creating certificates

    # Create one Certificate row per recipient
    for recipient in data["recipients"]:
        cert = Certificate(
            job_id=job.id,
            recipient_name=recipient["recipient_name"],
            recipient_email=recipient["recipient_email"],
        )
        db.session.add(cert)

    db.session.commit()

    # Kick off background processing
    start_job_worker(current_app._get_current_object(), job.id)  # type: ignore[attr-defined]

    return jsonify({"message": "Job created.", "job": job.to_dict()}), 202


@jobs_bp.get("/jobs/<string:job_id>")
def get_job(job_id: str):
    """
    Return the current status and progress counts for a job.

    Responses
    ---------
    200  Job found — returns job JSON.
    404  Job not found.
    """
    job: Job | None = db.session.get(Job, job_id)
    if job is None:
        return jsonify({"error": f"Job '{job_id}' not found."}), 404

    return jsonify({"job": job.to_dict()}), 200


# ── Certificate endpoints ─────────────────────────────────────────────────────


@jobs_bp.get("/jobs/<string:job_id>/certificates")
def list_certificates(job_id: str):
    """
    List all certificate records belonging to a job.

    Optional query params
    ---------------------
    status : filter by status (pending | success | failed)

    Responses
    ---------
    200  List of certificate objects (may be empty).
    404  Job not found.
    """
    job: Job | None = db.session.get(Job, job_id)
    if job is None:
        return jsonify({"error": f"Job '{job_id}' not found."}), 404

    status_filter = request.args.get("status")
    query = Certificate.query.filter_by(job_id=job_id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    certificates = query.all()
    return jsonify({"certificates": [c.to_dict() for c in certificates]}), 200


@jobs_bp.get("/jobs/<string:job_id>/certificates/<string:cert_id>")
def get_certificate(job_id: str, cert_id: str):
    """
    Return the detail of a single certificate.

    Responses
    ---------
    200  Certificate found.
    404  Job or certificate not found.
    """
    job: Job | None = db.session.get(Job, job_id)
    if job is None:
        return jsonify({"error": f"Job '{job_id}' not found."}), 404

    cert: Certificate | None = Certificate.query.filter_by(
        id=cert_id, job_id=job_id
    ).first()
    if cert is None:
        return jsonify({"error": f"Certificate '{cert_id}' not found in job '{job_id}'."}), 404

    return jsonify({"certificate": cert.to_dict()}), 200


@jobs_bp.get("/jobs/<string:job_id>/certificates/<string:cert_id>/download")
def download_certificate(job_id: str, cert_id: str):
    """
    Stream the generated PDF to the client as an attachment.

    Responses
    ---------
    200  PDF file.
    404  Job or certificate not found.
    409  Certificate is not yet generated (still pending or failed).
    """
    job: Job | None = db.session.get(Job, job_id)
    if job is None:
        return jsonify({"error": f"Job '{job_id}' not found."}), 404

    cert: Certificate | None = Certificate.query.filter_by(
        id=cert_id, job_id=job_id
    ).first()
    if cert is None:
        return jsonify({"error": f"Certificate '{cert_id}' not found in job '{job_id}'."}), 404

    if cert.status != "success":
        return (
            jsonify(
                {
                    "error": f"Certificate is not available for download (status: {cert.status}).",
                }
            ),
            409,
        )

    if not cert.file_path or not os.path.isfile(cert.file_path):
        return jsonify({"error": "Certificate file not found on disk."}), 500

    filename = f"certificate_{cert.recipient_name.replace(' ', '_')}.pdf"
    return send_file(
        cert.file_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
