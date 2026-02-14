"""Prometheus metrics for AgentGuard."""

from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info
from prometheus_client import Counter, Gauge, Histogram


# --- Business metrics ---

PROXY_REQUESTS_TOTAL = Counter(
    "agentguard_proxy_requests_total",
    "Total LLM proxy requests",
    ["provider", "model", "status"],
)

DETECTION_RESULTS_TOTAL = Counter(
    "agentguard_detection_results_total",
    "Detection results by category and action",
    ["category", "action"],
)

INCIDENTS_CREATED_TOTAL = Counter(
    "agentguard_incidents_created_total",
    "Total incidents created",
    ["severity", "category"],
)

PROXY_LATENCY = Histogram(
    "agentguard_proxy_latency_seconds",
    "LLM proxy request latency",
    ["provider"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

ACTIVE_CONNECTIONS = Gauge(
    "agentguard_active_connections",
    "Current active proxy connections",
)

CIRCUIT_BREAKER_STATE = Gauge(
    "agentguard_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["provider"],
)

RATE_LIMIT_REJECTIONS = Counter(
    "agentguard_rate_limit_rejections_total",
    "Total rate limit rejections",
    ["org_id"],
)

CELERY_TASKS_TOTAL = Counter(
    "agentguard_celery_tasks_total",
    "Celery task completions",
    ["task_name", "status"],
)


def setup_metrics(app):
    """Instrument FastAPI app with Prometheus metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/health/ready", "/health/detailed", "/metrics"],
        inprogress_name="agentguard_http_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
