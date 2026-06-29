"""
Unit tests for ResilienceAI core logic.
Tests run without external dependencies (no LLM, no DB).
"""

import sys
import asyncio
import json
from pathlib import Path

# Ensure agent-engine modules are importable
sys.path.insert(0, str(Path(__file__).parent / "packages" / "agent-engine"))

# We need to patch settings before importing anything that reads config
import importlib.util as iu
spec = iu.spec_from_file_location("config", str(Path(__file__).parent / "packages" / "agent-engine" / "app" / "config.py"))
pass

# Set dummy env vars before any imports try to read .env
import os
os.environ["LLM_API_KEY"] = "test-key"
os.environ["LLM_MODEL"] = "gpt-4o-mini"
os.environ["EMBEDDING_API_KEY"] = "test-key"
os.environ["MONGO_URI"] = "mongodb://localhost:27017"

TEST_PASSED = 0
TEST_FAILED = 0


def test(name):
    def decorator(fn):
        global TEST_PASSED, TEST_FAILED
        def wrapper():
            try:
                fn()
                print(f"  PASS: {name}")
                return True
            except AssertionError as e:
                print(f"  FAIL: {name} — {e}")
                return False
            except Exception as e:
                print(f"  FAIL: {name} — {type(e).__name__}: {e}")
                return False
        return wrapper
    return decorator


# ── Test 1: Log Parser Tool (no DB/API needed) ──
@test("parse_incident_logs strips timestamps")
def test_log_parser_timestamps():
    from app.tools.incident_parser import parse_incident_logs
    raw = "2024-06-15T14:32:01.123Z ERROR database connection timeout after 30s from 192.168.1.100"
    result = asyncio.run(parse_incident_logs(raw, "test-svc"))
    assert "[TIMESTAMP]" in result.sanitized_logs, f"Expected [TIMESTAMP], got: {result.sanitized_logs[:100]}"
    assert "[IP_ADDR]" in result.sanitized_logs, f"Expected [IP_ADDR], got: {result.sanitized_logs[:100]}"
    assert "192.168.1.100" not in result.sanitized_logs, "IP should be replaced"
    assert result.tokens_replaced > 0, f"Expected replacements, got {result.tokens_replaced}"


@test("parse_incident_logs strips memory addresses")
def test_log_parser_memory():
    from app.tools.incident_parser import parse_incident_logs
    raw = "SIGSEGV at 0x7fff1234abcd in libc.so.6"
    result = asyncio.run(parse_incident_logs(raw, "test-svc"))
    assert "[MEMORY_ADDR]" in result.sanitized_logs
    assert "0x7fff" not in result.sanitized_logs


@test("parse_incident_logs strips UUIDs")
def test_log_parser_uuid():
    from app.tools.incident_parser import parse_incident_logs
    raw = "Request failed: 550e8400-e29b-41d4-a716-446655440000"
    result = asyncio.run(parse_incident_logs(raw, "test-svc"))
    assert "[UUID]" in result.sanitized_logs
    assert "550e8400" not in result.sanitized_logs


@test("parse_incident_logs strips unix epochs")
def test_log_parser_epoch():
    from app.tools.incident_parser import parse_incident_logs
    raw = "Alert fired at 1718400000 for service"
    result = asyncio.run(parse_incident_logs(raw, "test-svc"))
    assert "[UNIX_EPOCH]" in result.sanitized_logs
    assert "1718400000" not in result.sanitized_logs


@test("parse_incident_logs preserves error structure")
def test_log_parser_structure():
    from app.tools.incident_parser import parse_incident_logs
    raw = "ERROR: connection pool exhausted for payment-service"
    result = asyncio.run(parse_incident_logs(raw, "test-svc"))
    assert "ERROR" in result.sanitized_logs
    assert "connection pool exhausted" in result.sanitized_logs
    assert "payment-service" in result.sanitized_logs


# ── Test 2: Alert Pydantic Schema Validation ──
@test("AlertCreate schema validates correct payload")
def test_alert_schema_valid():
    from app.schemas.alert import AlertCreate
    payload = {
        "serviceName": "payment-service",
        "environment": "production",
        "severity": "critical",
        "errorMessage": "Connection pool exhausted",
        "rawLogs": "some logs here",
    }
    alert = AlertCreate(**payload)
    assert alert.service_name == "payment-service"
    assert alert.severity.value == "critical"


@test("AlertCreate schema rejects missing serviceName")
def test_alert_schema_invalid():
    from app.schemas.alert import AlertCreate
    from pydantic import ValidationError
    try:
        AlertCreate(serviceName="", environment="prod", severity="high", errorMessage="err")
        raise AssertionError("Should have raised ValidationError")
    except ValidationError:
        pass  # Expected


# ── Test 3: Topology Tool (Pydantic contract) ──
@test("TopologyInput/Output have correct types")
def test_topology_contracts():
    from app.tools.topology import TopologyInput, TopologyOutput
    inp = TopologyInput(service_name="test-svc")
    assert inp.service_name == "test-svc"

    out = TopologyOutput(
        service_name="test-svc",
        upstream=["auth-service"],
        downstream=["notification-service"],
        found=True,
    )
    assert len(out.upstream) == 1
    assert out.found is True


# ── Test 4: Incident Beanie Model (Pydantic contract) ──
@test("Incident model has correct fields and defaults")
def test_incident_model():
    from app.models.incident import Incident, IncidentStatus

    doc = Incident(
        service_name="test-svc",
        status=IncidentStatus.INVESTIGATING,
    )
    assert doc.status == IncidentStatus.INVESTIGATING
    assert doc.alerts == []
    assert doc.remediation_steps == []
    assert doc.graph_execution_path == []
    assert doc.confidence_score is None


@test("IncidentStatus enum has required values")
def test_incident_status_enum():
    from app.models.incident import IncidentStatus
    assert IncidentStatus.INVESTIGATING.value == "Investigating"
    assert IncidentStatus.TRIAGE.value == "Triage"
    assert IncidentStatus.RESOLVED.value == "Resolved"


# ── Test 5: DiagnosisResponse schema ──
@test("DiagnosisResponse serializes correctly")
def test_diagnosis_response():
    from app.schemas.diagnosis import DiagnosisResponse

    resp = DiagnosisResponse(
        incident_id="INC-20240615-ABC123",
        service_name="payment-service",
        status="Triage",
        root_cause_analysis="Connection pool exhaustion due to misconfigured max_connections",
        remediation_steps=[
            "Increase max_connections from 100 to 500",
            "Add connection timeout monitoring alert",
        ],
        confidence_score=0.92,
        graph_execution_path=["router", "tool:query_knowledge_base", "evaluator", "complete"],
        upstream_affected=["auth-service", "api-gateway"],
        downstream_affected=["notification-service"],
        relevant_runbooks=["Connection Pool Tuning Guide"],
    )

    d = resp.model_dump()
    assert d["incident_id"] == "INC-20240615-ABC123"
    assert len(d["remediation_steps"]) == 2
    assert d["confidence_score"] == 0.92


# ── Test 6: KnowledgeBase Pydantic contracts ──
@test("KnowledgeBase Input/Output contracts")
def test_kb_contracts():
    from app.tools.knowledge_base import KnowledgeBaseInput, KnowledgeBaseOutput, RunbookMatch

    inp = KnowledgeBaseInput(query="connection timeout", target_service="payment-service", top_k=5)
    assert inp.target_service == "payment-service"
    assert inp.top_k == 5

    match = RunbookMatch(runbook_id="rb-1", title="Conn Pool Guide", content="Increase pool size", score=0.92)
    assert match.score == 0.92

    out = KnowledgeBaseOutput(matches=[match], query_used="connection timeout")
    assert len(out.matches) == 1


# ── Test 7: LangGraph graph compiles (no LLM needed for structure) ──
@test("LangGraph workflow compiles without errors")
def test_langgraph_compilation():
    from app.graph.workflow import build_incident_graph
    graph = build_incident_graph()
    compiled = graph.compile()
    assert compiled is not None
    # Verify node count
    nodes = compiled.get_graph().nodes
    node_names = {n for n in nodes}
    expected = {"router", "tool_topology", "tool_knowledge_base", "tool_log_parser", "evaluator", "__start__", "__end__"}
    overlapping = node_names & expected
    assert len(overlapping) >= 6, f"Expected at least 6 common nodes, got {len(overlapping)}: {overlapping}"


# ── Test 8: Log Parser pattern count ──
@test("Log parser has 9+ regex patterns defined")
def test_parser_pattern_count():
    from app.tools.incident_parser import REPLACEMENT_PATTERNS
    assert len(REPLACEMENT_PATTERNS) >= 9, f"Expected >=9 patterns, got {len(REPLACEMENT_PATTERNS)}"


# ── Test 9: Topology not-found case ──
@test("TopologyOutput handles not-found case")
def test_topology_not_found():
    from app.tools.topology import TopologyOutput
    out = TopologyOutput(service_name="nonexistent", upstream=[], downstream=[], found=False)
    assert out.found is False
    assert out.upstream == []


# ── Test 10: Config reads env vars ──
@test("Config loads from environment variables")
def test_config_env():
    from app.config import settings
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.agent_engine_port == 8000


# ═══════════════════════════════════════
# TypeScript counterpart verification (manual syntax check via Node)
# ═══════════════════════════════════════

# ── Test 11: Zod alert schema shape matches Pydantic ──
@test("Alert fields match across Zod and Pydantic")
def test_schema_alignment():
    from app.schemas.alert import AlertCreate
    pydantic_fields = set(AlertCreate.model_fields.keys())
    # Zod fields (from schemas/alert.ts): serviceName, environment, severity, errorMessage, rawLogs
    zod_fields = {"service_name", "environment", "severity", "error_message", "raw_logs"}
    assert pydantic_fields == zod_fields, f"Mismatch: {pydantic_fields.symmetric_difference(zod_fields)}"


# ═══════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  ResilienceAI — Verification Suite")
    print("=" * 60)

    test_log_parser_timestamps()
    test_log_parser_memory()
    test_log_parser_uuid()
    test_log_parser_epoch()
    test_log_parser_structure()
    test_alert_schema_valid()
    test_alert_schema_invalid()
    test_topology_contracts()
    test_incident_model()
    test_incident_status_enum()
    test_diagnosis_response()
    test_kb_contracts()
    test_langgraph_compilation()
    test_parser_pattern_count()
    test_topology_not_found()
    test_config_env()
    test_schema_alignment()
