"""
Tests for retrieving generated certificates.

Covers:
  - Listing all certificates for a job
  - Filtering by status
  - Getting a single certificate's detail
  - Downloading the PDF (success and error cases)
"""

import json
import time
import pytest


def _create_and_wait(client, payload, timeout=15):
    """Create a job and wait for it to complete, then return the job dict."""
    resp = client.post(
        "/api/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 202
    job_id = resp.get_json()["job"]["id"]

    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}").get_json()["job"]
        if body["status"] not in ("pending", "processing"):
            return body
        time.sleep(0.3)
    raise TimeoutError(f"Job {job_id} did not complete in time")


class TestRetrieveCertificates:
    """Tests for the certificate retrieval endpoints."""

    def test_list_certificates_returns_200(self, client, valid_payload):
        """GET /api/jobs/<id>/certificates must return 200."""
        job = _create_and_wait(client, valid_payload)
        resp = client.get(f"/api/jobs/{job['id']}/certificates")
        assert resp.status_code == 200

    def test_list_certificates_count(self, client, valid_payload):
        """Number of certificates must match the number of recipients."""
        job = _create_and_wait(client, valid_payload)
        certs = client.get(f"/api/jobs/{job['id']}/certificates").get_json()["certificates"]
        assert len(certs) == len(valid_payload["recipients"])

    def test_list_certificates_for_unknown_job_returns_404(self, client):
        resp = client.get("/api/jobs/no-such-job/certificates")
        assert resp.status_code == 404

    def test_filter_certificates_by_status(self, client, valid_payload):
        """?status=success filter should return only successful certs."""
        job = _create_and_wait(client, valid_payload)
        resp = client.get(f"/api/jobs/{job['id']}/certificates?status=success")
        certs = resp.get_json()["certificates"]
        assert all(c["status"] == "success" for c in certs)
        assert len(certs) == job["succeeded"]

    def test_get_single_certificate(self, client, valid_payload):
        """GET /api/jobs/<job_id>/certificates/<cert_id> must return 200."""
        job = _create_and_wait(client, valid_payload)
        certs = client.get(f"/api/jobs/{job['id']}/certificates").get_json()["certificates"]
        cert_id = certs[0]["id"]

        resp = client.get(f"/api/jobs/{job['id']}/certificates/{cert_id}")
        assert resp.status_code == 200
        assert resp.get_json()["certificate"]["id"] == cert_id

    def test_get_unknown_certificate_returns_404(self, client, valid_payload):
        job = _create_and_wait(client, valid_payload)
        resp = client.get(f"/api/jobs/{job['id']}/certificates/bad-cert-id")
        assert resp.status_code == 404

    def test_download_certificate_returns_pdf(self, client, valid_payload):
        """Downloading a successful certificate must return a PDF."""
        job = _create_and_wait(client, valid_payload)
        certs = client.get(
            f"/api/jobs/{job['id']}/certificates?status=success"
        ).get_json()["certificates"]

        assert len(certs) > 0, "No successful certificates to download"
        cert_id = certs[0]["id"]

        resp = client.get(f"/api/jobs/{job['id']}/certificates/{cert_id}/download")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"
        # Verify PDF magic bytes
        assert resp.data[:4] == b"%PDF"

    def test_download_pending_certificate_returns_409(self, client, app):
        """
        Attempting to download a certificate that hasn't been generated yet
        must return 409 Conflict.
        """
        import unittest.mock as mock
        import threading

        # We need a cert that stays "pending" — use an event to pause the worker
        pause_event = threading.Event()

        def blocking_generate(*args, **kwargs):
            pause_event.wait()  # block until we resume
            from app.certificate_generator import generate_certificate as real_fn
            return real_fn(*args, **kwargs)

        payload = {
            "event_name": "Pending Test",
            "issuer_name": "Org",
            "recipients": [{"recipient_name": "Pending User", "recipient_email": "p@example.com"}],
        }

        with mock.patch("app.worker.generate_certificate", side_effect=blocking_generate):
            resp = client.post(
                "/api/jobs",
                data=json.dumps(payload),
                content_type="application/json",
            )
            job_id = resp.get_json()["job"]["id"]

            # At this point the cert is pending (worker is blocked)
            # Give the thread a moment to pick it up and reach the blocking call
            time.sleep(0.5)

            with app.app_context():
                from app.models import Certificate
                cert = Certificate.query.filter_by(job_id=job_id).first()
                cert_id = cert.id

            dl_resp = client.get(
                f"/api/jobs/{job_id}/certificates/{cert_id}/download"
            )
            assert dl_resp.status_code == 409

            # Unblock the worker so the thread can finish cleanly
            pause_event.set()
