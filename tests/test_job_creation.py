"""
Tests for POST /api/jobs — job creation endpoint.
"""

import json
import pytest


class TestCreateJob:
    """Tests for creating a certificate generation job."""

    def test_create_job_returns_202(self, client_no_worker, valid_payload):
        """A valid request must return HTTP 202 Accepted."""
        resp = client_no_worker.post(
            "/api/jobs",
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        assert resp.status_code == 202

    def test_create_job_response_body(self, client_no_worker, valid_payload):
        """Response must contain a job object with expected fields."""
        resp = client_no_worker.post(
            "/api/jobs",
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        body = resp.get_json()
        assert "job" in body
        job = body["job"]

        assert job["event_name"] == valid_payload["event_name"]
        assert job["issuer_name"] == valid_payload["issuer_name"]
        assert job["status"] in ("pending", "processing", "completed")
        assert job["total"] == len(valid_payload["recipients"])
        assert "id" in job

    def test_create_job_persists_to_db(self, client_no_worker, valid_payload):
        """The created job must be retrievable via the GET endpoint."""
        resp = client_no_worker.post(
            "/api/jobs",
            data=json.dumps(valid_payload),
            content_type="application/json",
        )
        job_id = resp.get_json()["job"]["id"]

        get_resp = client_no_worker.get(f"/api/jobs/{job_id}")
        assert get_resp.status_code == 200
        job = get_resp.get_json()["job"]
        assert job["id"] == job_id
        assert job["event_name"] == valid_payload["event_name"]

    def test_create_job_no_body_returns_400(self, client_no_worker):
        """Missing request body must return 400."""
        resp = client_no_worker.post("/api/jobs", content_type="application/json")
        assert resp.status_code == 400

    def test_create_job_non_json_returns_400(self, client_no_worker):
        """Non-JSON content-type must return 400."""
        resp = client_no_worker.post("/api/jobs", data="not json")
        assert resp.status_code == 400


class TestIndexRoute:
    """Tests for the root GET / discovery route."""

    def test_index_returns_200_and_metadata(self, client_no_worker):
        resp = client_no_worker.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "running"
        assert "endpoints" in data
