from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: dict | None = None):
        super().__init__(code="NOT_FOUND", message=message, details=details, status_code=404)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed", details: dict | None = None):
        super().__init__(code="VALIDATION_ERROR", message=message, details=details, status_code=422)


class AuthorizationError(AppError):
    def __init__(self, message: str = "Not authorized", details: dict | None = None):
        super().__init__(code="AUTHORIZATION_ERROR", message=message, details=details, status_code=403)


class AIProcessingError(AppError):
    def __init__(self, message: str = "AI processing failed", details: dict | None = None):
        super().__init__(code="AI_PROCESSING_ERROR", message=message, details=details, status_code=502)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": {}}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
