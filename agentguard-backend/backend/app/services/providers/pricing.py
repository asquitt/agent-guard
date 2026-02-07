"""LLM provider pricing tables and cost calculation."""

from __future__ import annotations

# Cost per 1M tokens: (input, output)
OPENAI_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
    "text-embedding-ada-002": (0.10, 0.0),
}

ANTHROPIC_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-6": (15.00, 75.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
}

GEMINI_PRICING: dict[str, tuple[float, float]] = {
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}

AZURE_OPENAI_PRICING: dict[str, tuple[float, float]] = {
    # Azure uses same models as OpenAI with same pricing
    **OPENAI_PRICING,
}

BEDROCK_PRICING: dict[str, tuple[float, float]] = {
    "anthropic.claude-3-5-sonnet": (3.00, 15.00),
    "anthropic.claude-3-haiku": (0.25, 1.25),
    "amazon.titan-text-express": (0.20, 0.60),
    "amazon.titan-text-lite": (0.15, 0.20),
    "meta.llama3-70b-instruct": (2.65, 3.50),
    "meta.llama3-8b-instruct": (0.30, 0.60),
    "mistral.mistral-large": (4.00, 12.00),
    "mistral.mistral-small": (0.10, 0.30),
}

# Combined lookup table (order matters for prefix matching)
ALL_PRICING: dict[str, tuple[float, float]] = {
    **OPENAI_PRICING,
    **ANTHROPIC_PRICING,
    **GEMINI_PRICING,
    **BEDROCK_PRICING,
}


def _lookup_pricing(model: str, table: dict[str, tuple[float, float]]) -> tuple[float, float] | None:
    """Find pricing by exact match, then longest prefix match."""
    if model in table:
        return table[model]
    for known in sorted(table, key=len, reverse=True):
        if model.startswith(known):
            return table[known]
    return None


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD. Returns 0.0 for unknown models."""
    pricing = _lookup_pricing(model, ALL_PRICING)
    if pricing is None:
        return 0.0
    input_price, output_price = pricing
    cost = (input_tokens * input_price / 1_000_000) + (output_tokens * output_price / 1_000_000)
    return round(cost, 6)
