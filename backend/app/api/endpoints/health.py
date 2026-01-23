"""
Health check endpoints.
Used by Railway and monitoring systems.
"""
from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": settings.env,
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - verifies service is ready to accept traffic.
    Checks critical dependencies.
    """
    checks = {
        "api": True,
        "config": True,
    }

    # TODO: Add checks for:
    # - Redis connection
    # - Supabase connection
    # - API key validity

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - simple ping to verify process is running.
    Used by Kubernetes/Railway for container health.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
