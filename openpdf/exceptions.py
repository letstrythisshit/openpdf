"""Custom exception hierarchy for OpenPDF."""
from __future__ import annotations


class OpenPdfError(Exception):
    """Base exception for all OpenPDF errors."""


class FileDataError(OpenPdfError):
    """Raised when the PDF data is corrupt or unreadable."""


class PasswordError(OpenPdfError):
    """Raised when a password is required or incorrect."""


class PageNumberError(OpenPdfError, IndexError):
    """Raised for out-of-range page numbers."""


class AnnotationError(OpenPdfError):
    """Raised for invalid annotation operations."""


class FormFieldError(OpenPdfError):
    """Raised for invalid form-field operations."""


class EncryptionError(OpenPdfError):
    """Raised for encryption/decryption failures."""


class DependencyError(OpenPdfError, ImportError):
    """Raised when an optional dependency is missing (e.g. pytesseract)."""
