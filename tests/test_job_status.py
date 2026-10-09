"""
Tests for job status / progress endpoint (GET /api/jobs/<job_id>).
"""

import json
import time
import pytest


def _create_job(client, payload):
    resp = client.post(
        "/api/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 202
    return resp.get_json()["job"]


class TestJobStatus:
    """Tests for checking job progress and status."""

    def test_get_job_returns_200(self, client_no_worker, valid_payload):
        """GET /api/jobs/<id> must return 200 for an existing job."""
        job = _create_job(client_no_worker, valid_payload)
        resp = client_no_worker.get(f"/api/jobs/{job['id']}")
        assert resp.status_code == 200

    def test_get_job_unknown_id_returns_404(self, client_no_worker):
        """Non-existent job ID must return 404."""
        resp = client_no_worker.get("/api/jobs/does-not-exist")
        assert resp.status_code == 404

    def test_job_status_fields_present(self, client_no_worker, valid_payload):
        """Status response must include required fields."""
        job = _create_job(client_no_worker, valid_payload)
        resp = client_no_worker.get(f"/api/jobs/{job['id']}")
        body = resp.get_json()["job"]

        required_fields = {
            "id", "event_name", "issuer_name", "status",
            "total", "succeeded", "failed", "pending",
            "created_at", "updated_at",
        }
        assert required_fields.issubset(body.keys())

    def test_job_total_matches_recipients(self, client_no_worker, valid_payload):
        """total count must equal the number of recipients submitted."""
        job = _create_job(client_no_worker, valid_payload)
        resp = client_no_worker.get(f"/api/jobs/{job['id']}")
        body = resp.get_json()["job"]
        assert body["total"] == len(valid_payload["recipients"])

    def test_job_eventually_completes(self, client, valid_payload):
        """
        Poll the status endpoint until the job leaves the 'processing'
        state or until a generous timeout.  It must end as 'completed'.
        """
        job = _create_job(client, valid_payload)
        job_id = job["id"]

        deadline = time.time() + 15  # 15 second timeout
        while time.time() < deadline:
            resp = client.get(f"/api/jobs/{job_id}")
            status = resp.get_json()["job"]["status"]
            if status not in ("pending", "processing"):
                break
            time.sleep(0.3)

        assert status == "completed"

    def test_succeeded_count_after_completion(self, client, valid_payload):
        """After completion, succeeded == total for valid recipients."""
        job = _create_job(client, valid_payload)
        job_id = job["id"]

        deadline = time.time() + 15
        while time.time() < deadline:
            body = client.get(f"/api/jobs/{job_id}").get_json()["job"]
            if body["status"] not in ("pending", "processing"):
                break
            time.sleep(0.3)

        assert body["succeeded"] == body["total"]
        assert body["failed"] == 0
