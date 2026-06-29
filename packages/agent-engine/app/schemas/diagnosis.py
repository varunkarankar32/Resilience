"""
ResilienceAI — Diagnosis Schema
Response model for agent-engine diagnosis results.
"""

from pydantic import BaseModel
from typing import Optional


class DiagnosisResponse(BaseModel):
    """Schema for diagnosis output returned to webhooks-gateway."""
    incident_id: str
    service_name: str
    status: str
    root_cause_analysis: Optional[str] = None
    remediation_steps: list[str] = []
    confidence_score: Optional[float] = None
    graph_execution_path: list[str] = []
    upstream_affected: list[str] = []
    downstream_affected: list[str] = []
    relevant_runbooks: list[str] = []
