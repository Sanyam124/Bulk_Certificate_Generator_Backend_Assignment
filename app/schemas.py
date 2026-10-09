import re
from marshmallow import Schema, fields, validates, ValidationError, validate


def _is_valid_email(email: str) -> bool:
    """Simple RFC-5322-inspired e-mail regex check."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


class RecipientSchema(Schema):
    """Schema for a single certificate recipient."""

    recipient_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={"required": "recipient_name is required."},
    )
    recipient_email = fields.Email(
        required=True,
        error_messages={"required": "recipient_email is required."},
    )

    @validates("recipient_name")
    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("recipient_name must not be blank.")

    @validates("recipient_email")
    def validate_email(self, value):
        if not _is_valid_email(value):
            raise ValidationError(f"'{value}' is not a valid email address.")


class JobCreateSchema(Schema):
    """Schema for the POST /jobs request body."""

    event_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={"required": "event_name is required."},
    )
    issuer_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={"required": "issuer_name is required."},
    )
    recipients = fields.List(
        fields.Nested(RecipientSchema),
        required=True,
        validate=validate.Length(min=1, error="recipients list must not be empty."),
        error_messages={"required": "recipients is required."},
    )
