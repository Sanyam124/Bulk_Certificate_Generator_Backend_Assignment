"""
Shared pytest fixtures used across all test modules.
"""

import os
import shutil
import pytest
import unittest.mock as mock

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """
    Create a Flask application configured for testing.

    Uses an in-memory SQLite database (TestingConfig.SQLALCHEMY_DATABASE_URI
    = "sqlite:///:memory:") so tests are fast and fully isolated from the
    production database.
    """
    flask_app = create_app(TestingConfig)

    # Ensure a clean certificate output directory for each test session
    cert_dir = flask_app.config["CERTIFICATES_DIR"]
    if os.path.isdir(cert_dir):
        shutil.rmtree(cert_dir)
    os.makedirs(cert_dir, exist_ok=True)

    yield flask_app

    # Teardown: remove generated test certificates
    if os.path.isdir(cert_dir):
        shutil.rmtree(cert_dir)


@pytest.fixture(scope="session")
def db(app):
    """Create all tables once for the test session."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_db(db, app):
    """
    Reset DB state between tests by deleting all rows after each test.

    We also wait for any background cert-worker threads that were spawned
    during the test to finish before clearing the database, so they don't
    race against the cleanup DELETE statements.
    """
    yield

    import threading
    import time as _time

    deadline = _time.time() + 10
    while _time.time() < deadline:
        workers = [
            t for t in threading.enumerate()
            if t.name.startswith("cert-worker-")
        ]
        if not workers:
            break
        _time.sleep(0.1)

    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def client_no_worker(app):
    """
    Flask test client with the background worker stubbed out.

    Use this in tests that only care about the HTTP layer (validation,
    response shapes, status codes) and do NOT need actual certificate
    generation. This prevents background threads from conflicting with
    the test's DB cleanup.
    """
    with mock.patch("app.routes.start_job_worker"):
        yield app.test_client()


@pytest.fixture()
def valid_payload():
    """A valid job creation payload with two recipients."""
    return {
        "event_name": "Python Bootcamp 2025",
        "issuer_name": "Acme Academy",
        "recipients": [
            {
                "recipient_name": "Alice Smith",
                "recipient_email": "alice@example.com",
            },
            {
                "recipient_name": "Bob Jones",
                "recipient_email": "bob@example.com",
            },
        ],
    }
