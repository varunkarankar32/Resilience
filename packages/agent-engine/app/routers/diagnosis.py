"""
ResilienceAI — Diagnosis Router
POST /api/v1/diagnose — Receives alert payloads from webhooks-gateway,
runs LangGraph diagnosis, returns structured results, and persists to MongoDB.
"""

from fastapi import APIRouter, HTTPException
from app.schemas.alert import AlertCreate
from app.schemas.diagnosis import DiagnosisResponse
from app.graph.workflow import run_diagnosis_and_persist
from datetime import datetime
import uuid

router = APIRouter(prefix="/diagnose", tags=["Diagnosis"])


@router.post("", response_model=DiagnosisResponse)
async def diagnose_incident(alert: AlertCreate):
    """Run LangGraph-powered incident diagnosis.

    Receives an alert from webhooks-gateway, invokes the LangGraph workflow
    (router → tool execution → evaluator loop), returns structured
    diagnosis including root cause analysis, remediation steps, and
    confidence scoring. Persists results to MongoDB.

    Args:
        alert: Structured alert payload from the gateway.

    Returns:
        DiagnosisResponse with RCA, remediation steps, and confidence.
    """
    if not alert.service_name or not alert.error_message:
        raise HTTPException(status_code=400, detail="serviceName and errorMessage are required")

    result = await run_diagnosis_and_persist(
        service_name=alert.service_name,
        environment=alert.environment,
        severity=alert.severity.value,
        error_message=alert.error_message,
        raw_logs=alert.raw_logs or "",
    )

    return DiagnosisResponse(
        incident_id=f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        service_name=alert.service_name,
        status="Triage" if result["confidence_score"] >= 0.8 else "Investigating",
        root_cause_analysis=result["root_cause_analysis"] or None,
        remediation_steps=result["remediation_steps"],
        confidence_score=result["confidence_score"],
        graph_execution_path=result["execution_path"],
        upstream_affected=result.get("topology_upstream", []),
        downstream_affected=result.get("topology_downstream", []),
        relevant_runbooks=[m.get("title", "") for m in result.get("runbook_matches", [])],
    )
