"""
Tests for input validation (POST /api/jobs).

These tests ensure that the validation layer correctly rejects malformed
or incomplete requests and returns meaningful error messages.
"""

import json
import pytest


class TestInputValidation:
    """Validation tests for the job creation endpoint."""

    def _post(self, client, payload):
        return client.post(
            "/api/jobs",
            data=json.dumps(payload),
            content_type="application/json",
        )

    # ── Missing top-level fields ───────────────────────────────────────────

    def test_missing_event_name(self, client_no_worker, valid_payload):
        del valid_payload["event_name"]
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400
        assert "event_name" in resp.get_json()["details"]

    def test_missing_issuer_name(self, client_no_worker, valid_payload):
        del valid_payload["issuer_name"]
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400
        assert "issuer_name" in resp.get_json()["details"]

    def test_missing_recipients(self, client_no_worker, valid_payload):
        del valid_payload["recipients"]
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400
        assert "recipients" in resp.get_json()["details"]

    def test_empty_recipients_list(self, client_no_worker, valid_payload):
        valid_payload["recipients"] = []
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400

    # ── Invalid recipient fields ───────────────────────────────────────────

    def test_recipient_missing_name(self, client_no_worker, valid_payload):
        valid_payload["recipients"][0].pop("recipient_name")
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400

    def test_recipient_missing_email(self, client_no_worker, valid_payload):
        valid_payload["recipients"][0].pop("recipient_email")
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400

    def test_recipient_invalid_email_format(self, client_no_worker, valid_payload):
        valid_payload["recipients"][0]["recipient_email"] = "not-an-email"
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400

    def test_recipient_blank_name(self, client_no_worker, valid_payload):
        valid_payload["recipients"][0]["recipient_name"] = "   "
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400

    def test_blank_event_name(self, client_no_worker, valid_payload):
        valid_payload["event_name"] = ""
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400

    # ── Partial failures don't block valid recipients ──────────────────────

    def test_valid_recipients_alongside_invalid(self, client_no_worker, valid_payload):
        """
        The API-level validation rejects the entire request if ANY recipient
        has invalid data — this is by design (fail fast before creating the
        job).  The per-certificate failure isolation happens at the generation
        stage, tested separately.
        """
        valid_payload["recipients"].append(
            {"recipient_name": "Bad Actor", "recipient_email": "not-valid"}
        )
        resp = self._post(client_no_worker, valid_payload)
        assert resp.status_code == 400
