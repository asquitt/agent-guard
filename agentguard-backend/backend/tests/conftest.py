"""Comprehensive test fixtures for AgentGuard backend tests."""

import uuid
import uuid as _uuid_mod

import pytest
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy import JSON, StaticPool, String, event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import create_access_token
from app.core.database import Base
from app.core.deps import get_db
from app.main import app
from app.models import Detector, Organization, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- SQLite compatibility: map PostgreSQL types to SQLite equivalents ---
# This lets us use the same models in-memory without changing production code.
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # type: ignore[no-untyped-def]
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):  # type: ignore[no-untyped-def]
    return "VARCHAR(36)"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):  # type: ignore[no-untyped-def]
    return "JSON"


# --- SQLite UUID bind parameter fix ---
# PostgreSQL UUID columns with as_uuid=True use a bind_processor that calls .hex
# on values. In SQLite we store UUIDs as VARCHAR(36), so we need to override
# the bind_processor to convert both UUID objects and strings to plain strings.
_original_uuid_bind_processor = UUID.bind_processor


def _sqlite_uuid_bind_processor(self, dialect):  # type: ignore[no-untyped-def]
    """Override UUID bind_processor to handle strings for SQLite."""
    if dialect.name == "sqlite":
        def process(value):  # type: ignore[no-untyped-def]
            if value is None:
                return value
            if isinstance(value, _uuid_mod.UUID):
                return str(value)
            return str(value)
        return process
    return _original_uuid_bind_processor(self, dialect)


UUID.bind_processor = _sqlite_uuid_bind_processor  # type: ignore[assignment]

# Also fix result_processor to convert strings back to UUID objects
_original_uuid_result_processor = UUID.result_processor


def _sqlite_uuid_result_processor(self, dialect, coltype):  # type: ignore[no-untyped-def]
    """Override UUID result_processor to return UUID objects from strings."""
    if dialect.name == "sqlite":
        def process(value):  # type: ignore[no-untyped-def]
            if value is None:
                return value
            if isinstance(value, _uuid_mod.UUID):
                return value
            return _uuid_mod.UUID(str(value))
        return process
    return _original_uuid_result_processor(self, dialect, coltype)


UUID.result_processor = _sqlite_uuid_result_processor  # type: ignore[assignment]


# In-memory SQLite async engine for tests
TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
async def _setup_db():
    """Create all tables before each test, drop after."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Async DB session with automatic rollback after each test."""
    async with TestSessionLocal() as session:
        # Enable SQLite foreign key support
        await session.execute(
            __import__("sqlalchemy").text("PRAGMA foreign_keys=ON")
        )
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession):
    """Async HTTP client with test DB dependency override."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def org(db_session: AsyncSession) -> Organization:
    """Create a test Organization."""
    organization = Organization(
        id=uuid.uuid4(),
        name="Test Organization",
        slug="test-org",
        plan_tier="starter",
        settings={},
    )
    db_session.add(organization)
    await db_session.flush()
    return organization


@pytest.fixture
async def user(db_session: AsyncSession, org: Organization) -> User:
    """Create a test User with ADMIN role."""
    test_user = User(
        id=uuid.uuid4(),
        email="testadmin@agentguard.dev",
        hashed_password=pwd_context.hash("TestPassword1!"),
        full_name="Test Admin",
        role="admin",
        org_id=org.id,
        is_active=True,
        token_version=0,
        failed_login_attempts=0,
    )
    db_session.add(test_user)
    await db_session.flush()
    return test_user


@pytest.fixture
def auth_token(user: User) -> str:
    """Create a valid JWT access token for the test user."""
    return create_access_token(str(user.id), token_version=0)


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization headers with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


# --------------- Detector fixtures ---------------

async def _create_detector(
    db_session: AsyncSession, org: Organization, name: str, category: str
) -> Detector:
    detector = Detector(
        id=uuid.uuid4(),
        org_id=org.id,
        name=name,
        category=category,
        is_active=True,
        action_mode="monitor",
        config={},
    )
    db_session.add(detector)
    await db_session.flush()
    return detector


@pytest.fixture
async def pii_detector(db_session: AsyncSession, org: Organization) -> Detector:
    return await _create_detector(db_session, org, "PII Leak Detector", "pii_leak")


@pytest.fixture
async def compliance_detector(db_session: AsyncSession, org: Organization) -> Detector:
    return await _create_detector(db_session, org, "Compliance Detector", "compliance")


@pytest.fixture
async def cost_detector(db_session: AsyncSession, org: Organization) -> Detector:
    return await _create_detector(db_session, org, "Cost Anomaly Detector", "cost_anomaly")


@pytest.fixture
async def loop_detector(db_session: AsyncSession, org: Organization) -> Detector:
    return await _create_detector(db_session, org, "Loop Detector", "loop")


@pytest.fixture
async def hallucination_detector(db_session: AsyncSession, org: Organization) -> Detector:
    return await _create_detector(db_session, org, "Hallucination Detector", "hallucination")


# --------------- Sample request/response payloads ---------------

@pytest.fixture
def sample_openai_request() -> dict:
    """Typical OpenAI chat completion request body."""
    return {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": "What is the current interest rate?"},
        ],
        "temperature": 0.7,
        "max_tokens": 256,
    }


@pytest.fixture
def sample_openai_response() -> dict:
    """Typical OpenAI chat completion response body."""
    return {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The current federal funds rate is set by the Federal Reserve.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 25, "completion_tokens": 18, "total_tokens": 43},
    }


@pytest.fixture
def sample_anthropic_request() -> dict:
    """Typical Anthropic messages request body."""
    return {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 256,
        "messages": [
            {"role": "user", "content": "Summarize our Q3 earnings report."},
        ],
    }


@pytest.fixture
def sample_anthropic_response() -> dict:
    """Typical Anthropic messages response body."""
    return {
        "id": "msg_01XYZ",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Q3 earnings showed a 12% increase in revenue year-over-year.",
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 15, "output_tokens": 22},
    }
