from flask import Flask
from .extensions import db
from .config import Config


def create_app(config_class=Config):
    """Application factory pattern for Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from .routes import jobs_bp
    app.register_blueprint(jobs_bp, url_prefix="/api")

    @app.get("/")
    def index():
        return {
            "name": "Bulk Certificate Generator API",
            "version": "1.0.0",
            "status": "running",
            "documentation": "See README.md for complete API specification and curl examples.",
            "endpoints": {
                "create_job": "POST /api/jobs",
                "get_job_status": "GET /api/jobs/<job_id>",
                "list_certificates": "GET /api/jobs/<job_id>/certificates",
                "get_certificate": "GET /api/jobs/<job_id>/certificates/<cert_id>",
                "download_certificate": "GET /api/jobs/<job_id>/certificates/<cert_id>/download",
            },
        }, 200

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
