from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.models.errors import (
    AppError,
    AuthError,
    NotFoundError,
    ValidationError,
    ExternalServiceError,
    create_api_error_response,
)
from app.routers import health, me, profile, portfolio, recommendations, chat

app = FastAPI(title="Financial Advisor Backend")

# CORS middleware for mobile app development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers for consistent error responses
@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    """Handle authentication/authorization errors."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=create_api_error_response(
            code=exc.code,
            message=exc.message,
            details=None
        )
    )


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle resource not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=create_api_error_response(
            code=exc.code,
            message=exc.message,
            details=None
        )
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_api_error_response(
            code=exc.code,
            message=exc.message,
            details=None
        )
    )


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError):
    """Handle external service errors."""
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=create_api_error_response(
            code=exc.code,
            message=exc.message,
            details=None
        )
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Handle other application-specific errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_api_error_response(
            code=exc.code,
            message=exc.message,
            details=None
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with a generic error response."""
    from app.config import get_settings
    settings = get_settings()
    # Only show details in development
    details = str(exc) if settings.ENV == "development" else None
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_api_error_response(
            code="InternalServerError",
            message="An unexpected error occurred",
            details=details
        )
    )

# Register routers
app.include_router(health.router)
app.include_router(me.router)
app.include_router(profile.router)
app.include_router(portfolio.router)
app.include_router(recommendations.router)
app.include_router(chat.router)
