"""PII Redaction Engine for FitForge AI."""

import re
from typing import Any, Dict, List, Union


class PIIRedactor:
    """Redacts Personally Identifiable Information (PII) from strings, logs, traces, and dicts."""

    # Regex patterns for common PII
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
    PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
    IPV4_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Redact sensitive PII from a string."""
        if not isinstance(text, str):
            return text

        redacted = text
        redacted = cls.EMAIL_PATTERN.sub('[REDACTED_EMAIL]', redacted)
        redacted = cls.PHONE_PATTERN.sub('[REDACTED_PHONE]', redacted)
        redacted = cls.SSN_PATTERN.sub('[REDACTED_SSN]', redacted)
        redacted = cls.CREDIT_CARD_PATTERN.sub('[REDACTED_CARD]', redacted)
        redacted = cls.IPV4_PATTERN.sub('[REDACTED_IP]', redacted)
        return redacted

    @classmethod
    def redact_data(cls, data: Any) -> Any:
        """Recursively redact PII from dictionaries, lists, or strings."""
        if isinstance(data, str):
            return cls.redact_text(data)
        elif isinstance(data, dict):
            return {k: cls.redact_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.redact_data(item) for item in data]
        return data
