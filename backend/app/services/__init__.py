"""Business-logic services.

Application use-cases sit between the API and the data layer. Services
orchestrate repositories, agents, and external integrations.
"""
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.exceptions import (
    DocumentNotFoundError,
    EmailAlreadyExistsError,
    EmptyFileError,
    FileTooLargeError,
    InactiveUserError,
    InvalidCredentialsError,
    UnsupportedFileTypeError,
)

__all__ = [
    "AuthService",
    "DocumentService",
    "EmailAlreadyExistsError",
    "InvalidCredentialsError",
    "InactiveUserError",
    "DocumentNotFoundError",
    "EmptyFileError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
]
