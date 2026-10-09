"""
Tests for individual certificate failure isolation.

The key requirement: one certificate failing must NOT prevent other valid
certificates in the same job from being generated.

Strategy: we monkey-patch generate_certificate so that it raises an
exception for a specific recipient name, then verify that:
  - the affected certificate is marked "failed" with an error message
  - all other certificates are still "success"
  - the overall job status is "completed" (partial success), not "failed"
"""

import json
import time
import unittest.mock as mock

import pytest


def _create_job(client, payload):
    resp = client.post(
        "/api/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 202
    return resp.get_json()["job"]


def _wait_for_completion(client, job_id, timeout=15):
    """Poll GET /api/jobs/<id> until the job leaves processing state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}").get_json()["job"]
        if body["status"] not in ("pending", "processing"):
            return body
        time.sleep(0.3)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


class TestCertificateFailureIsolation:
    """Tests that verify a single failure doesn't abort the whole job."""

    def test_failed_certificate_has_error_message(self, client, app):
        """
        When PDF generation fails for one recipient, that certificate record
        must have status='failed' and a non-empty error_message.
        """
        payload = {
            "event_name": "Failure Isolation Test",
            "issuer_name": "Test Org",
            "recipients": [
                {"recipient_name": "Will Fail", "recipient_email": "fail@example.com"},
                {"recipient_name": "Will Pass", "recipient_email": "pass@example.com"},
            ],
        }

        # Patch generate_certificate to raise for "Will Fail"
        original = "app.worker.generate_certificate"
        real_generate = None

        def mock_generate(output_dir, certificate_id, recipient_name, **kwargs):
            from app.certificate_generator import generate_certificate as real_fn
            if recipient_name == "Will Fail":
                raise RuntimeError("Simulated generation failure")
            return real_fn(
                output_dir=output_dir,
                certificate_id=certificate_id,
                recipient_name=recipient_name,
                **kwargs,
            )

        with mock.patch(original, side_effect=mock_generate):
            job = _create_job(client, payload)
            job_body = _wait_for_completion(client, job["id"])

        # Overall job should be "completed" (not fully failed) since one passed
        assert job_body["status"] == "completed"
        assert job_body["succeeded"] == 1
        assert job_body["failed"] == 1

        # Inspect individual certificates
        certs_resp = client.get(f"/api/jobs/{job['id']}/certificates")
        certs = certs_resp.get_json()["certificates"]

        failed_certs = [c for c in certs if c["status"] == "failed"]
        success_certs = [c for c in certs if c["status"] == "success"]

        assert len(failed_certs) == 1
        assert failed_certs[0]["recipient_name"] == "Will Fail"
        assert failed_certs[0]["error_message"] is not None
        assert "Simulated generation failure" in failed_certs[0]["error_message"]

        assert len(success_certs) == 1
        assert success_certs[0]["recipient_name"] == "Will Pass"

    def test_all_failed_job_status_is_failed(self, client):
        """If ALL certificates fail, the job status must be 'failed'."""
        payload = {
            "event_name": "All Fail Test",
            "issuer_name": "Test Org",
            "recipients": [
                {"recipient_name": "Fail 1", "recipient_email": "f1@example.com"},
                {"recipient_name": "Fail 2", "recipient_email": "f2@example.com"},
            ],
        }

        def always_fail(*args, **kwargs):
            raise RuntimeError("Always fails")

        with mock.patch("app.worker.generate_certificate", side_effect=always_fail):
            job = _create_job(client, payload)
            job_body = _wait_for_completion(client, job["id"])

        assert job_body["status"] == "failed"
        assert job_body["failed"] == 2
        assert job_body["succeeded"] == 0
