"""
Certificate PDF generator using ReportLab.

Design decisions:
- A single predefined A4-landscape template is used for all certificates.
- Generation is a pure function — it receives all data, writes a PDF file, and
  returns the file path.  This makes it easy to unit-test in isolation.
- All visual constants (colors, fonts, sizes) are defined at the top of the
  module so they can be found and changed in one place.
"""

import os
from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


# ── Visual constants ──────────────────────────────────────────────────────────
PAGE_W, PAGE_H = landscape(A4)   # 297 mm × 210 mm in points

# Colour palette
GOLD = colors.HexColor("#C9A84C")
DARK_NAVY = colors.HexColor("#1A2340")
LIGHT_CREAM = colors.HexColor("#FDF8F0")
BORDER_COLOR = GOLD

# Font names (built-in ReportLab fonts — no external font files required)
FONT_TITLE = "Helvetica-Bold"
FONT_BODY = "Helvetica"
FONT_ITALIC = "Helvetica-Oblique"

# Margins
MARGIN = 18 * mm


def generate_certificate(
    output_dir: str,
    certificate_id: str,
    recipient_name: str,
    recipient_email: str,
    event_name: str,
    issuer_name: str,
    issue_date: date | None = None,
) -> str:
    """
    Generate a PDF certificate and save it to *output_dir*.

    Parameters
    ----------
    output_dir       : directory where the PDF will be written
    certificate_id   : unique identifier used as the filename
    recipient_name   : full name printed on the certificate
    recipient_email  : email printed below the recipient name
    event_name       : name of the course / event
    issuer_name      : organisation or person issuing the certificate
    issue_date       : date of issue (defaults to today)

    Returns
    -------
    str – absolute path to the generated PDF file

    Raises
    ------
    OSError  – if the output directory cannot be created or the file cannot
                be written (callers should catch this and mark the certificate
                as failed rather than letting it propagate).
    """
    if issue_date is None:
        issue_date = date.today()

    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{certificate_id}.pdf")

    c = canvas.Canvas(file_path, pagesize=landscape(A4))
    _draw_certificate(c, recipient_name, recipient_email, event_name, issuer_name, issue_date)
    c.save()

    return os.path.abspath(file_path)


# ── Private drawing helpers ───────────────────────────────────────────────────

def _draw_certificate(
    c: canvas.Canvas,
    recipient_name: str,
    recipient_email: str,
    event_name: str,
    issuer_name: str,
    issue_date: date,
) -> None:
    """Draw every element onto the ReportLab canvas."""

    _draw_background(c)
    _draw_borders(c)
    _draw_header(c)
    _draw_body(c, recipient_name, recipient_email, event_name)
    _draw_footer(c, issuer_name, issue_date)


def _draw_background(c: canvas.Canvas) -> None:
    c.setFillColor(LIGHT_CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def _draw_borders(c: canvas.Canvas) -> None:
    # Outer thick gold border
    c.setStrokeColor(BORDER_COLOR)
    c.setLineWidth(6)
    c.rect(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, fill=0, stroke=1)

    # Inner thin gold border (decorative)
    inner = 5 * mm
    c.setLineWidth(1.5)
    c.rect(
        MARGIN + inner,
        MARGIN + inner,
        PAGE_W - 2 * (MARGIN + inner),
        PAGE_H - 2 * (MARGIN + inner),
        fill=0,
        stroke=1,
    )


def _draw_header(c: canvas.Canvas) -> None:
    # "CERTIFICATE" title
    c.setFillColor(DARK_NAVY)
    c.setFont(FONT_TITLE, 44)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 55 * mm, "CERTIFICATE")

    # Subtitle
    c.setFont(FONT_ITALIC, 18)
    c.setFillColor(GOLD)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 68 * mm, "of Completion")

    # Decorative gold line
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    line_y = PAGE_H - 75 * mm
    c.line(MARGIN + 30 * mm, line_y, PAGE_W - MARGIN - 30 * mm, line_y)


def _draw_body(
    c: canvas.Canvas,
    recipient_name: str,
    recipient_email: str,
    event_name: str,
) -> None:
    center_x = PAGE_W / 2
    body_top = PAGE_H - 90 * mm

    # "This is to certify that"
    c.setFont(FONT_BODY, 14)
    c.setFillColor(DARK_NAVY)
    c.drawCentredString(center_x, body_top, "This is to certify that")

    # Recipient name — large, gold
    c.setFont(FONT_TITLE, 34)
    c.setFillColor(GOLD)
    c.drawCentredString(center_x, body_top - 18 * mm, recipient_name)

    # Recipient email — small, grey
    c.setFont(FONT_ITALIC, 11)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawCentredString(center_x, body_top - 27 * mm, recipient_email)

    # Completion sentence
    c.setFont(FONT_BODY, 14)
    c.setFillColor(DARK_NAVY)
    c.drawCentredString(
        center_x, body_top - 38 * mm, "has successfully completed"
    )

    # Event name — navy bold
    c.setFont(FONT_TITLE, 20)
    c.setFillColor(DARK_NAVY)
    c.drawCentredString(center_x, body_top - 50 * mm, event_name)


def _draw_footer(c: canvas.Canvas, issuer_name: str, issue_date: date) -> None:
    footer_y = MARGIN + 22 * mm

    # Signature line (left)
    sig_x = MARGIN + 40 * mm
    c.setStrokeColor(DARK_NAVY)
    c.setLineWidth(1)
    c.line(sig_x, footer_y, sig_x + 60 * mm, footer_y)

    c.setFont(FONT_BODY, 11)
    c.setFillColor(DARK_NAVY)
    c.drawCentredString(sig_x + 30 * mm, footer_y - 6 * mm, issuer_name)
    c.setFont(FONT_ITALIC, 9)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawCentredString(sig_x + 30 * mm, footer_y - 11 * mm, "Issuer")

    # Date (right)
    date_x = PAGE_W - MARGIN - 70 * mm
    c.setStrokeColor(DARK_NAVY)
    c.line(date_x, footer_y, date_x + 60 * mm, footer_y)

    c.setFont(FONT_BODY, 11)
    c.setFillColor(DARK_NAVY)
    c.drawCentredString(
        date_x + 30 * mm,
        footer_y - 6 * mm,
        issue_date.strftime("%B %d, %Y"),
    )
    c.setFont(FONT_ITALIC, 9)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawCentredString(date_x + 30 * mm, footer_y - 11 * mm, "Date of Issue")
