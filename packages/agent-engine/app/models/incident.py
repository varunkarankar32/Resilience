"""
ResilienceAI — Incident Model
MongoDB document representing an active or resolved SRE incident.
"""

from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional
from enum import Enum


class IncidentStatus(str, Enum):
    INVESTIGATING = "Investigating"
    TRIAGE = "Triage"
    RESOLVED = "Resolved"


class AlertEntry(Document):
    """Embedded sub-document for each alert within an incident."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    log: str = Field(max_length=10000)


class Incident(Document):
    """Top-level incident document."""
    service_name: str = Field(index=True)
    status: IncidentStatus = Field(default=IncidentStatus.INVESTIGATING)
    alerts: list[AlertEntry] = Field(default_factory=list)
    root_cause_analysis: Optional[str] = None
    remediation_steps: list[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    graph_execution_path: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    class Settings:
        name = "incidents"
