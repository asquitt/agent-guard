"""AgentGuard API - AI Agent Incident Response Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.auth import limiter
from app.core.config import settings
from app.core.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware

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

# Security middleware (outermost = applied last, so order matters)
# 1. Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)
# 2. Request body size limit (10 MB)
app.add_middleware(RequestSizeLimitMiddleware)

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
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME}


# Router registration
from app.api import (  # noqa: E402
    alerts,
    api_keys,
    auth,
    billing,
    compliance,
    dashboard,
    detectors,
    incidents,
    organizations,
    proxy,
    proxy_endpoints,
    retention,
    sso,
    webhooks,
    websocket,
)

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
app.include_router(websocket.router, tags=["WebSocket"])
