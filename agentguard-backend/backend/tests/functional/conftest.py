"""Shared state, config, and helpers for functional tests.

All test modules import from here to share the global state dict,
HTTP helpers, and pass/fail counters.
"""

import time

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = "http://localhost:8001"
TS = int(time.time())
PASSWORD = "FuncTest1!Strong"
NEW_PASSWORD = "NewFuncT1!Strong"

# State dict carries IDs between test groups
S: dict = {}

# Counters
passed = 0
failed = 0
errors: list[str] = []

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def section(name: str) -> None:
    print(f"\n{CYAN}--- {name} ---{RESET}")


def ok(label: str, status: int, ms: int) -> None:
    global passed
    passed += 1
    print(f"  {GREEN}[PASS]{RESET} {label:<55} ({status})  {ms}ms")


def fail(label: str, expected: int, got: int, body: str = "") -> None:
    global failed
    failed += 1
    detail = f" | {body[:120]}" if body else ""
    msg = f"  {RED}[FAIL]{RESET} {label:<55} (expected {expected}, got {got}){detail}"
    print(msg)
    errors.append(f"{label}: expected {expected}, got {got}")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _h(token: str | None = None) -> dict:
    """Build auth header."""
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def check(
    label: str,
    method: str,
    path: str,
    expected: int,
    *,
    json: dict | list | None = None,
    token: str | None = None,
    headers: dict | None = None,
) -> requests.Response | None:
    """Execute request and print pass/fail."""
    url = f"{BASE}{path}"
    hdrs = headers if headers is not None else _h(token)
    t0 = time.time()
    try:
        r = requests.request(method, url, json=json, headers=hdrs, timeout=10)
    except Exception as e:
        fail(label, expected, -1, str(e))
        return None
    ms = int((time.time() - t0) * 1000)
    if r.status_code == expected:
        ok(label, r.status_code, ms)
    else:
        fail(label, expected, r.status_code, r.text[:200] if r.text else "")
    return r


def register(email: str, name: str, org: str) -> dict | None:
    """Register and return tokens."""
    r = check(
        f"Register {org}",
        "POST",
        "/api/v1/auth/register",
        201,
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": name,
            "org_name": org,
            "controlled_evaluation_accepted": True,
        },
    )
    if r and r.status_code == 201:
        return r.json()
    return None


def login(email: str, password: str = PASSWORD) -> dict | None:
    """Login and return tokens."""
    r = check(
        f"Login {email.split('@')[0]}",
        "POST",
        "/api/v1/auth/login",
        200,
        json={"email": email, "password": password},
    )
    if r and r.status_code == 200:
        return r.json()
    return None
