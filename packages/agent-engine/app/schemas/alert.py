"""
ResilienceAI — Alert Schema
Pydantic model for incoming alert payloads. Matches the Zod schema in webhooks-gateway.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertCreate(BaseModel):
    """Schema for alert ingestion."""
    service_name: str = Field(..., alias="serviceName", min_length=1, max_length=255)
    environment: str = Field(..., min_length=1, max_length=100)
    severity: AlertSeverity
    error_message: str = Field(..., alias="errorMessage", min_length=1, max_length=5000)
    raw_logs: Optional[str] = Field(default="", alias="rawLogs", max_length=50000)

    class Config:
        populate_by_name = True
