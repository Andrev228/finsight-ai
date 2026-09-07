"""Deterministic input privacy guardrails."""

import re

EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)",
)
SSN_PATTERN = re.compile(r"(?<!\d)\d{3}[-\s]\d{2}[-\s]\d{4}(?!\d)")
IBAN_PATTERN = re.compile(
    r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]){11,30}\b",
    re.IGNORECASE,
)
LONG_NUMBER_PATTERN = re.compile(r"(?<!\w)(?:\d[ -]?){7,18}\d(?!\w)")


def redact_pii(value: str) -> str:
    redacted = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    redacted = PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    redacted = SSN_PATTERN.sub("[REDACTED_GOVERNMENT_ID]", redacted)
    redacted = IBAN_PATTERN.sub("[REDACTED_BANK_ID]", redacted)
    return LONG_NUMBER_PATTERN.sub("[REDACTED_NUMBER]", redacted)
