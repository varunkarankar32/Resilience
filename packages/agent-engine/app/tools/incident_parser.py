"""
ResilienceAI — Incident Log Parser Tool
Uses regex to sanitize variable text from raw logs before LLM analysis.
"""

import re
from pydantic import BaseModel, Field


class LogParserInput(BaseModel):
    raw_logs: str = Field(description="Unsanitized log output from the incident")
    service_name: str = Field(description="Service name for context")


class LogParserOutput(BaseModel):
    sanitized_logs: str
    detected_patterns: list[str]
    tokens_replaced: int


# Patterns that contain variable data not useful for LLM analysis
REPLACEMENT_PATTERNS: list[tuple[str, str, str]] = [
    # Timestamps (ISO 8601, Unix epoch, common formats)
    (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", "[TIMESTAMP]", "ISO timestamp"),
    (r"\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s[+-]\d{4}", "[APACHE_TIMESTAMP]", "Apache timestamp"),
    (r"\b\d{10,13}\b", "[UNIX_EPOCH]", "Unix epoch timestamp"),

    # Memory addresses
    (r"0x[0-9a-fA-F]{6,16}", "[MEMORY_ADDR]", "Memory address"),

    # IP addresses
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_ADDR]", "IP address"),

    # UUIDs
    (r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "[UUID]", "UUID"),

    # Request/Transaction IDs (common patterns)
    (r"\b[a-f0-9]{16,32}\b", "[TRANSACTION_ID]", "Transaction ID"),

    # Port numbers after colons (but not IP:port)
    (r":\d{4,5}\b", ":[PORT]", "Port number"),

    # Stack trace file paths (handled separately to avoid over-matching)
    (r"(?:/[-\w.]+)+\.(?:py|java|go|ts|js|rb):\d+", "[STACK_TRACE]", "Stack trace line"),
]


async def parse_incident_logs(raw_logs: str, service_name: str) -> LogParserOutput:
    """Sanitize variable text from raw logs using regex patterns.

    This tool removes variable data (timestamps, memory addresses, IPs, UUIDs, etc.)
    from raw log output, leaving only the structural error patterns. The sanitized
    output is what the LLM analyzes — this dramatically improves embedding quality
    and prevents the model from hallucinating on specific values.

    Args:
        raw_logs: Unsanitized log output from monitoring/alerting systems.
        service_name: Contextual service name (currently unused, for future pattern selection).

    Returns:
        LogParserOutput with sanitized logs and count of tokens replaced.
    """
    sanitized = raw_logs
    detected: list[str] = []
    total_replacements = 0

    for pattern, replacement, pattern_name in REPLACEMENT_PATTERNS:
        matches = re.findall(pattern, sanitized)
        if matches:
            detected.append(pattern_name)
            sanitized = re.sub(pattern, replacement, sanitized)
            total_replacements += len(matches)

    # Strip excessive whitespace from replacements
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    sanitized = sanitized.strip()

    return LogParserOutput(
        sanitized_logs=sanitized,
        detected_patterns=detected,
        tokens_replaced=total_replacements,
    )
