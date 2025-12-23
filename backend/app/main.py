from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.models.errors import AppError, create_error_response
from app.routers import health, me, profile, portfolio, recommendations

app = FastAPI(title="Financial Advisor Backend")

# CORS middleware for mobile app development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for consistent error responses
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Handle application-specific errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            error=type(exc).__name__,
            detail=str(exc)
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with a generic error response."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            error="InternalServerError",
            detail="An unexpected error occurred"
        )
    )

# Register routers
app.include_router(health.router)
app.include_router(me.router)
app.include_router(profile.router)
app.include_router(portfolio.router)
app.include_router(recommendations.router)
