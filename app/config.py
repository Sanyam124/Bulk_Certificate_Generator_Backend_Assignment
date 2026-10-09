import os


class Config:
    """Base configuration class."""

    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///certificates.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Certificate output directory
    CERTIFICATES_DIR = os.environ.get(
        "CERTIFICATES_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "certificates"),
    )


class TestingConfig(Config):
    """Configuration for running tests."""

    TESTING = True
    # Use an in-memory SQLite database for fast, isolated tests
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Store test certificates in a temp-like directory within the project
    CERTIFICATES_DIR = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "test_certificates"
    )
