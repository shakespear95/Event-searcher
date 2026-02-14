"""
Secret Nature / Whats Up App - FastAPI Application
Main entry point for the backend API.
"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints import health, search, users
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

# Configure logging
configure_logging(
    log_level=settings.log_level,
    json_logs=settings.is_production,
)

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(
        "Starting Secret Nature / Whats Up App",
        env=settings.env,
        debug=settings.debug,
    )
    yield
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title="Secret Nature / Whats Up App",
    description="Event discovery API with verified sources and weather-aware recommendations",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = datetime.utcnow()

    # Log request
    logger.info(
        "Request received",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    response = await call_next(request)

    # Log response
    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    return response


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Secret Nature / Whats Up App API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
