from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from app.models.errors import (
    AppError,
    AuthError,
    NotFoundError,
    ValidationError,
    ExternalServiceError,
    create_api_error_response,
)
from app.routers import health, me, profile, portfolio, recommendations, chat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions (including authentication errors from HTTPBearer)."""
    # Convert authentication-related HTTPExceptions to our format
    if exc.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        # Check if this is an authentication error
        if "not authenticated" in exc.detail.lower() or "not authorized" in exc.detail.lower():
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=create_api_error_response(
                    code="AUTH_REQUIRED",
                    message="Authentication required. Please provide a valid Bearer token.",
                    details=None
                )
            )
    
    # For other HTTPExceptions, return them as-is but in our format
    return JSONResponse(
        status_code=exc.status_code,
        content=create_api_error_response(
            code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            details=None
        )
    )


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


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors (422)."""
    # Extract the first error message for clarity
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        field_path = " -> ".join(str(loc) for loc in first_error.get("loc", []))
        error_msg = first_error.get("msg", "Validation error")
        error_type = first_error.get("type", "validation_error")
        message = f"Validation error in {field_path}: {error_msg}"
    else:
        message = "Request validation failed"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_api_error_response(
            code="VALIDATION_ERROR",
            message=message,
            details=errors
        )
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle application validation errors."""
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
