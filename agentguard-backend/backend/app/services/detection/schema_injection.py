"""Schema injection detector -- structural analysis of function/tool schemas for adversarial patterns."""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

_SEVERITY_RANK: dict[str, int] = {
    IncidentSeverity.INFO.value: 0,
    IncidentSeverity.LOW.value: 1,
    IncidentSeverity.MEDIUM.value: 2,
    IncidentSeverity.HIGH.value: 3,
    IncidentSeverity.CRITICAL.value: 4,
}

# Forced-prefix / instruction-like content in description fields (CRITICAL)
_DESCRIPTION_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:should|must|always)\s+start\s+with\b", re.IGNORECASE),
    re.compile(r"(?:begin|prefix)\s+(?:your\s+)?(?:response|output|answer)\s+with\b", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules)", re.IGNORECASE),
    re.compile(r"(?:you\s+are|act\s+as|pretend\s+to\s+be)\b", re.IGNORECASE),
    re.compile(r"system\s*(?:prompt|override|instruction)\s*:", re.IGNORECASE),
    re.compile(r"override\s+(?:all\s+)?(?:previous|safety|content)\s+(?:rules|filters)", re.IGNORECASE),
    re.compile(r"from\s+now\s+on\b", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"do\s+not\s+(?:follow|obey|listen)", re.IGNORECASE),
    re.compile(r"\bstep\s+should\s+start\s+with\b", re.IGNORECASE),
]

# Adversarial enum values (HIGH)
_ENUM_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(?:previous|all)", re.IGNORECASE),
    re.compile(r"override\s+(?:instructions|rules|safety)", re.IGNORECASE),
    re.compile(r"system\s*(?:prompt|message|override)", re.IGNORECASE),
    re.compile(r"you\s+(?:are|must|should|will)", re.IGNORECASE),
    re.compile(r"(?:execute|run|call)\s+(?:this|the)\s+(?:command|function|code)", re.IGNORECASE),
    re.compile(r"bypass\s+(?:safety|security|filter|restriction)", re.IGNORECASE),
]

# Instruction-like field names (HIGH)
_FIELD_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(?:system_prompt|instruction|override|ignore_rules|jailbreak)", re.IGNORECASE),
    re.compile(r"(?:hidden|secret|internal)_(?:instruction|prompt|command)", re.IGNORECASE),
    re.compile(r"^_(?:sys|admin|root|exec)", re.IGNORECASE),
]

_MAX_REQUIRED_FIELDS = 50


def _extract_schemas(body: dict[str, object]) -> list[dict[str, object]]:
    """Extract all JSON schemas from a request body (tools, functions, response_format)."""
    schemas: list[dict[str, object]] = []

    # OpenAI tools format
    tools = body.get("tools")
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict):
                func = tool.get("function")
                if isinstance(func, dict):
                    schemas.append(func)

    # OpenAI functions format (legacy)
    functions = body.get("functions")
    if isinstance(functions, list):
        for func in functions:
            if isinstance(func, dict):
                schemas.append(func)

    # Structured output / response_format
    resp_fmt = body.get("response_format")
    if isinstance(resp_fmt, dict):
        for key in ("json_schema", "schema"):
            val = resp_fmt.get(key)
            if isinstance(val, dict):
                schemas.append(val)

    # Top-level json_schema
    top_schema = body.get("json_schema")
    if isinstance(top_schema, dict):
        schemas.append(top_schema)

    return schemas


def _check_text_field(
    text: str,
    patterns: list[re.Pattern[str]],
    path: str,
    pattern_type: str,
    severity: str,
    detail_prefix: str,
) -> dict[str, str] | None:
    """Check a string field against patterns. Returns first match or None."""
    for pat in patterns:
        if pat.search(text):
            return {
                "field_path": path,
                "pattern_type": pattern_type,
                "severity": severity,
                "detail": f"{detail_prefix}: {pat.pattern[:80]}",
            }
    return None


def _scan_schema(schema: dict[str, object], path: str = "$") -> list[dict[str, str]]:
    """Recursively scan a schema dict for adversarial patterns."""
    findings: list[dict[str, str]] = []

    # Check description, title, and default fields for injection patterns
    for field_name, ptype, sev, prefix in [
        ("description", "description_injection", IncidentSeverity.CRITICAL.value, "Injection pattern in description"),
        ("title", "description_injection", IncidentSeverity.HIGH.value, "Injection pattern in title"),
        ("default", "forced_prefix", IncidentSeverity.CRITICAL.value, "Injection in default value"),
    ]:
        val = schema.get(field_name)
        if isinstance(val, str):
            hit = _check_text_field(val, _DESCRIPTION_INJECTION_PATTERNS, f"{path}.{field_name}", ptype, sev, prefix)
            if hit:
                findings.append(hit)

    # Check enum values for adversarial content
    enum_vals = schema.get("enum")
    if isinstance(enum_vals, list):
        for val in enum_vals:
            if isinstance(val, str):
                hit = _check_text_field(
                    val, _ENUM_INJECTION_PATTERNS, f"{path}.enum",
                    "adversarial_enum", IncidentSeverity.HIGH.value,
                    f"Adversarial enum value: {val[:100]}",
                )
                if hit:
                    # Use the enum value itself as detail, not the pattern
                    hit["detail"] = f"Adversarial enum value: {val[:100]}"
                    findings.append(hit)

    # Check for excessive required fields
    required = schema.get("required")
    if isinstance(required, list) and len(required) > _MAX_REQUIRED_FIELDS:
        findings.append({
            "field_path": f"{path}.required",
            "pattern_type": "excessive_required",
            "severity": IncidentSeverity.HIGH.value,
            "detail": f"Excessive required fields: {len(required)} (threshold: {_MAX_REQUIRED_FIELDS})",
        })

    # Recurse into properties and check field names
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for prop_name, prop_schema in properties.items():
            for pat in _FIELD_NAME_PATTERNS:
                if pat.search(prop_name):
                    findings.append({
                        "field_path": f"{path}.properties.{prop_name}",
                        "pattern_type": "suspicious_field_name",
                        "severity": IncidentSeverity.HIGH.value,
                        "detail": f"Instruction-like field name: {prop_name}",
                    })
                    break
            if isinstance(prop_schema, dict):
                findings.extend(_scan_schema(prop_schema, f"{path}.properties.{prop_name}"))

    # Recurse into nested structures
    for key in ("items", "parameters", "schema"):
        nested = schema.get(key)
        if isinstance(nested, dict):
            findings.extend(_scan_schema(nested, f"{path}.{key}"))

    return findings


class SchemaInjectionDetector:
    """Sync detector for schema-level injection attacks.

    Inspects function calling schemas and structured output schemas for
    adversarial patterns that weaponize the model's strict adherence to structure.
    Pure structural analysis -- no LLM verification needed.
    """

    category: str = DetectorCategory.SCHEMA_INJECTION.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        try:
            body = json.loads(request_body)
        except (json.JSONDecodeError, TypeError):
            return self._pass("Request body is not valid JSON")

        if not isinstance(body, dict):
            return self._pass("Request body is not a JSON object")

        schemas = _extract_schemas(body)
        if not schemas:
            return self._pass("No schemas found in request")

        all_findings: list[dict[str, str]] = []
        for schema in schemas:
            all_findings.extend(_scan_schema(schema))

        if not all_findings:
            return self._pass("No schema injection patterns detected")

        # Determine highest severity
        highest = IncidentSeverity.INFO.value
        for f in all_findings:
            if _SEVERITY_RANK.get(f["severity"], 0) > _SEVERITY_RANK.get(highest, 0):
                highest = f["severity"]

        pattern_types = {f["pattern_type"] for f in all_findings}
        summary = ", ".join(sorted(pattern_types))

        return DetectionResult(
            detected=True,
            severity=highest,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Schema injection: {summary}",
            description=(
                f"Found {len(all_findings)} adversarial pattern(s) across "
                f"{len(schemas)} schema(s) in request"
            ),
            details={
                "findings": all_findings,
                "schemas_scanned": len(schemas),
                "model": model or "unknown",
            },
        )

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
