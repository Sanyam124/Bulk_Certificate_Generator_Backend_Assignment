# Bulk Certificate Generator — Backend API

A Flask-based REST API that accepts bulk certificate generation requests, generates PDF certificates using a predefined template, and tracks job status in real-time.

---

## Table of Contents

1. [Project Setup](#1-project-setup)
2. [Running the Application](#2-running-the-application)
3. [Running Tests](#3-running-tests)
4. [API Usage Guide](#4-api-usage-guide)
   - [Create a Generation Job](#41-create-a-generation-job)
   - [Check Job Status](#42-check-job-status)
   - [List Certificates](#43-list-certificates-in-a-job)
   - [Get a Single Certificate](#44-get-a-single-certificate)
   - [Download a Certificate PDF](#45-download-a-certificate-pdf)
5. [Design Decisions](#5-design-decisions)

---

## 1. Project Setup

### Prerequisites

- Python 3.11+
- pip

### Install Dependencies

```bash
# Clone / navigate to the project root
cd Bulk_Certificate_Generator_Backend_Assignment

# (Recommended) Create a virtual environment
python -m venv venv

# Activate it
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables (optional)

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask secret key |
| `DATABASE_URL` | `sqlite:///certificates.db` | SQLAlchemy connection string |
| `CERTIFICATES_DIR` | `<project_root>/certificates` | Directory where PDFs are saved |

---

## 2. Running the Application

```bash
python run.py
```

The server starts on **http://localhost:5000**.

Alternatively, using the Flask CLI:

```bash
flask --app run:app run --debug
```

On first run, SQLite creates `instance/certificates.db` automatically — no migration step is needed.

---

## 3. Running Tests

```bash
pytest
```

The test suite uses an **in-memory SQLite database** (no files created on disk except PDFs in a temporary `test_certificates/` directory, which is cleaned up automatically after the session).

Run with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_certificate_generation.py -v
```

---

## 4. API Usage Guide

All endpoints are prefixed with `/api`.

### 4.1 Create a Generation Job

**`POST /api/jobs`**

Submit a list of recipients to start a bulk certificate generation job.
Returns immediately with HTTP **202 Accepted** — generation runs in the background.

**Request body**

```json
{
  "event_name": "Python Bootcamp 2025",
  "issuer_name": "Acme Academy",
  "recipients": [
    { "recipient_name": "Alice Smith",  "recipient_email": "alice@example.com" },
    { "recipient_name": "Bob Jones",    "recipient_email": "bob@example.com" },
    { "recipient_name": "Carol White",  "recipient_email": "carol@example.com" }
  ]
}
```

**Example (curl)**

```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Python Bootcamp 2025",
    "issuer_name": "Acme Academy",
    "recipients": [
      { "recipient_name": "Alice Smith", "recipient_email": "alice@example.com" },
      { "recipient_name": "Bob Jones",   "recipient_email": "bob@example.com" }
    ]
  }'
```

**Response (202)**

```json
{
  "message": "Job created.",
  "job": {
    "id": "a3f1b2c4-...",
    "event_name": "Python Bootcamp 2025",
    "issuer_name": "Acme Academy",
    "status": "pending",
    "total": 2,
    "succeeded": 0,
    "failed": 0,
    "pending": 2,
    "created_at": "2025-06-01T10:00:00+00:00",
    "updated_at": "2025-06-01T10:00:00+00:00"
  }
}
```

**Validation errors (400)**

```json
{
  "error": "Validation failed.",
  "details": {
    "recipients": {
      "0": { "recipient_email": ["Not a valid email address."] }
    }
  }
}
```

---

### 4.2 Check Job Status

**`GET /api/jobs/<job_id>`**

Poll this endpoint to track progress.

```bash
curl http://localhost:5000/api/jobs/a3f1b2c4-...
```

**Response (200)**

```json
{
  "job": {
    "id": "a3f1b2c4-...",
    "status": "completed",
    "total": 2,
    "succeeded": 2,
    "failed": 0,
    "pending": 0
  }
}
```

| `status` value | Meaning |
|---|---|
| `pending` | Job accepted, not yet started |
| `processing` | Worker is actively generating certificates |
| `completed` | All (or some) certificates were generated |
| `failed` | Every certificate failed |

---

### 4.3 List Certificates in a Job

**`GET /api/jobs/<job_id>/certificates`**

Returns all certificate records for a job.

Optional query parameter: `?status=success|failed|pending`

```bash
# All certificates
curl http://localhost:5000/api/jobs/a3f1b2c4-.../certificates

# Only failed ones
curl http://localhost:5000/api/jobs/a3f1b2c4-.../certificates?status=failed
```

**Response (200)**

```json
{
  "certificates": [
    {
      "id": "c1d2e3f4-...",
      "job_id": "a3f1b2c4-...",
      "recipient_name": "Alice Smith",
      "recipient_email": "alice@example.com",
      "status": "success",
      "error_message": null
    }
  ]
}
```

---

### 4.4 Get a Single Certificate

**`GET /api/jobs/<job_id>/certificates/<cert_id>`**

```bash
curl http://localhost:5000/api/jobs/a3f1b2c4-.../certificates/c1d2e3f4-...
```

---

### 4.5 Download a Certificate PDF

**`GET /api/jobs/<job_id>/certificates/<cert_id>/download`**

Streams the PDF file as an attachment. Returns **409** if the certificate is not yet generated.

```bash
curl -O -J http://localhost:5000/api/jobs/a3f1b2c4-.../certificates/c1d2e3f4-.../download
```

---

## 5. Design Decisions

### Background Processing — Python `threading`

**Choice:** Each job is processed by a daemon thread spawned via Python's built-in `threading` module.

**Why not Celery / Redis?**
- Zero external infrastructure required — just `pip install` and run.
- Simpler to understand, debug, and explain in an interview context.
- Perfectly adequate for the scale described in the problem statement.

**Trade-offs acknowledged:**
- Not horizontally scalable — each process has its own thread pool.
- No automatic retry on crash — if the process dies mid-job, pending certificates remain in `pending` state. A production system would use Celery + Redis (or a similar task queue) with retry logic and worker process management.

### Database — SQLite + SQLAlchemy

- SQLite requires no installation and stores data in a single file, making setup trivial.
- SQLAlchemy ORM provides a clean abstraction; switching to PostgreSQL requires only changing `DATABASE_URL`.

### Certificate Format — ReportLab PDF

- PDF is the industry standard for certificates — easily printable and not editable.
- ReportLab uses only built-in Python-bundled fonts so no external font files are required.
- The template is fully defined in `app/certificate_generator.py` with visual constants at the top of the file, making it easy to customise.

### Validation Strategy

- Marshmallow schemas validate the entire request body before any database writes occur.
- A single invalid recipient rejects the whole request (fail fast at the API boundary).
- Individual certificate failures during generation are isolated per-certificate and do **not** abort the rest of the job — this matches real-world requirements where one bad email address shouldn't block 999 others.

### Job Status Model

```
pending → processing → completed
                    ↘ failed  (only if ALL certificates fail)
```

`completed` with `failed > 0` represents a partial success. Clients can inspect the `failed` count and list certificates filtered by `?status=failed` to identify which recipients need to be resubmitted.

### Application Factory Pattern

`create_app()` in `app/__init__.py` follows Flask's recommended factory pattern. This allows multiple application instances with different configurations (e.g., `TestingConfig` uses an in-memory database), which is essential for running isolated tests.
