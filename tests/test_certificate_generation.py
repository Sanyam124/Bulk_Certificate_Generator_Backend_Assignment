"""
Tests for the certificate PDF generator module.

These tests call generate_certificate() directly — they do not go through
the HTTP layer — so they run quickly and are easy to isolate.
"""

import os
import pytest
from datetime import date

from app.certificate_generator import generate_certificate


class TestGenerateCertificate:
    """Unit tests for the certificate PDF generator."""

    def test_generates_pdf_file(self, tmp_path):
        """generate_certificate() must create a non-empty PDF file."""
        cert_id = "test-cert-001"
        file_path = generate_certificate(
            output_dir=str(tmp_path),
            certificate_id=cert_id,
            recipient_name="Alice Smith",
            recipient_email="alice@example.com",
            event_name="Python Bootcamp",
            issuer_name="Acme Academy",
        )

        assert os.path.isfile(file_path), "PDF file was not created"
        assert os.path.getsize(file_path) > 0, "PDF file is empty"

    def test_output_filename_uses_cert_id(self, tmp_path):
        """The generated file should be named <certificate_id>.pdf."""
        cert_id = "unique-id-xyz"
        file_path = generate_certificate(
            output_dir=str(tmp_path),
            certificate_id=cert_id,
            recipient_name="Bob Jones",
            recipient_email="bob@example.com",
            event_name="Data Science 101",
            issuer_name="Tech Corp",
        )

        assert os.path.basename(file_path) == f"{cert_id}.pdf"

    def test_returns_absolute_path(self, tmp_path):
        """The returned path must be absolute."""
        file_path = generate_certificate(
            output_dir=str(tmp_path),
            certificate_id="abs-path-test",
            recipient_name="Carol White",
            recipient_email="carol@example.com",
            event_name="Event",
            issuer_name="Issuer",
        )
        assert os.path.isabs(file_path)

    def test_creates_output_directory_if_missing(self, tmp_path):
        """Output directory should be created if it does not exist."""
        new_dir = str(tmp_path / "nested" / "output")
        assert not os.path.isdir(new_dir)

        generate_certificate(
            output_dir=new_dir,
            certificate_id="dir-create-test",
            recipient_name="Dave Green",
            recipient_email="dave@example.com",
            event_name="Workshop",
            issuer_name="Org",
        )
        assert os.path.isdir(new_dir)

    def test_custom_issue_date(self, tmp_path):
        """Passing a custom issue_date should not raise an error."""
        custom_date = date(2024, 6, 15)
        file_path = generate_certificate(
            output_dir=str(tmp_path),
            certificate_id="date-test",
            recipient_name="Eve Black",
            recipient_email="eve@example.com",
            event_name="Summer School",
            issuer_name="University",
            issue_date=custom_date,
        )
        assert os.path.isfile(file_path)

    def test_pdf_magic_bytes(self, tmp_path):
        """Generated file should start with the %PDF magic bytes."""
        file_path = generate_certificate(
            output_dir=str(tmp_path),
            certificate_id="magic-bytes-test",
            recipient_name="Frank Blue",
            recipient_email="frank@example.com",
            event_name="Conference",
            issuer_name="Issuer Name",
        )
        with open(file_path, "rb") as f:
            header = f.read(4)
        assert header == b"%PDF", "File does not appear to be a valid PDF"

    def test_invalid_output_dir_raises(self):
        """
        Passing a path where we cannot create a directory should raise an error.
        We simulate this by passing a file path as the output directory.
        """
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp_file:
            # tmp_file.name is a *file*, not a directory.
            # os.makedirs on a path whose parent is a file should raise.
            bad_dir = os.path.join(tmp_file.name, "subdir")
            with pytest.raises(Exception):
                generate_certificate(
                    output_dir=bad_dir,
                    certificate_id="bad-dir-test",
                    recipient_name="Grace",
                    recipient_email="grace@example.com",
                    event_name="Event",
                    issuer_name="Issuer",
                )
