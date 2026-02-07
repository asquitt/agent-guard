"""AgentGuard API - AI Agent Incident Response Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.auth import limiter
from app.core.config import settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.core.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.sentry import init_sentry

# Initialize observability before app creation
configure_logging()
init_sentry()

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent Incident Response for Financial Services",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Middleware (outermost = applied last, so order matters)
# 1. Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)
# 2. Request body size limit (10 MB)
app.add_middleware(RequestSizeLimitMiddleware)
# 3. Request logging with correlation IDs
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware — explicit methods/headers instead of wildcards
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)


@app.get("/health")
async def health_check():
    """Liveness probe — always returns 200 if the process is running."""
    return {"status": "healthy", "app": settings.APP_NAME}


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe — checks database and Redis connectivity."""
    import redis.asyncio as aioredis
    from sqlalchemy import text

    from app.core.database import AsyncSessionLocal

    checks: dict[str, str] = {}

    # Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    healthy = all(v == "ok" for v in checks.values())
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with per-component status and response times."""
    from fastapi.responses import JSONResponse

    from app.services import health_service

    result = await health_service.check_components()
    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=result)


# Router registration
from app.api import (  # noqa: E402
    agents,
    alerts,
    api_keys,
    auth,
    billing,
    compliance,
    dashboard,
    detectors,
    incidents,
    organizations,
    playground,
    proxy,
    proxy_endpoints,
    retention,
    sso,
    webhooks,
    websocket,
)

app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(sso.router, prefix="/api/v1/auth/sso", tags=["SSO"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["Organizations"])
app.include_router(proxy_endpoints.router, prefix="/api/v1/proxy-endpoints", tags=["Proxy Endpoints"])
app.include_router(detectors.router, prefix="/api/v1/detectors", tags=["Detectors"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["Incidents"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(proxy.router, prefix="/api/v1/proxy", tags=["LLM Proxy"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["Compliance"])
app.include_router(retention.router, prefix="/api/v1/retention", tags=["Retention"])
app.include_router(playground.router, prefix="/api/v1/playground", tags=["Playground"])
app.include_router(websocket.router, tags=["WebSocket"])
