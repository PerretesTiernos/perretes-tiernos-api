from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    """Base domain exception."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "resource_not_found"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "resource_conflict"


class DomainValidationError(AppError):
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    error_code = "domain_validation_error"


class RateLimitExceededError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limit_exceeded"


def setup_exception_handlers(app: FastAPI) -> None:
    """Registers homogeneous error responses across the API."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        sanitized_errors = [
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Los datos de entrada no superaron la validación.",
                    "details": sanitized_errors,
                }
            },
        )

