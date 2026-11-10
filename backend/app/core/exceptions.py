"""
Clipped-AI — Custom Exception Classes & FastAPI Exception Handlers
Provides consistent JSON error responses across the entire API.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ── Base exception ────────────────────────────────────────────────────────────
class ClippedAIException(Exception):
    """Base class for all Clipped-AI application exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


# ── Domain exceptions ─────────────────────────────────────────────────────────
class NotFoundError(ClippedAIException):
    def __init__(self, resource: str, resource_id: Any = None):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(msg, status_code=status.HTTP_404_NOT_FOUND)


class ForbiddenError(ClippedAIException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ConflictError(ClippedAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ValidationError(ClippedAIException):
    def __init__(self, message: str, detail: Any = None):
        super().__init__(
            message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class VideoProcessingError(ClippedAIException):
    def __init__(self, message: str, detail: Any = None):
        super().__init__(
            message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class StorageError(ClippedAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TranscriptionError(ClippedAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIServiceError(ClippedAIException):
    def __init__(self, message: str, detail: Any = None):
        super().__init__(
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )


class FileTooLargeError(ClippedAIException):
    def __init__(self, max_size_mb: int):
        super().__init__(
            f"File exceeds the {max_size_mb} MB limit",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class UnsupportedFormatError(ClippedAIException):
    def __init__(self, fmt: str, supported: list):
        super().__init__(
            f"Unsupported format '{fmt}'. Supported: {', '.join(supported)}",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


# ── Error response builder ────────────────────────────────────────────────────
def _error_response(
    request: Request,
    status_code: int,
    message: str,
    detail: Any = None,
) -> JSONResponse:
    body: Dict[str, Any] = {
        "success": False,
        "error": {
            "message": message,
            "status_code": status_code,
            "path": str(request.url.path),
        },
    }
    if detail is not None:
        body["error"]["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


# ── Register handlers on the FastAPI app ──────────────────────────────────────
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ClippedAIException)
    async def handle_clipped_ai_exception(
        request: Request, exc: ClippedAIException
    ) -> JSONResponse:
        return _error_response(request, exc.status_code, exc.message, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            exc.errors(),
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        from app.core.logging_config import get_logger

        log = get_logger("exceptions")
        log.exception("Unhandled exception on %s", request.url.path)
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred. Please try again.",
        )
