from flask_sqlalchemy import SQLAlchemy

# Single SQLAlchemy instance shared across the application.
# Initialized in create_app() to avoid circular imports.
db = SQLAlchemy()
