"""
ResilienceAI — ServiceTopology Model
Documents microservice dependency maps for blast-radius analysis.
"""

from beanie import Document
from pydantic import Field
from datetime import datetime


class ServiceTopology(Document):
    """Service dependency topology."""
    service_name: str = Field(unique=True, index=True)
    upstream_dependencies: list[str] = Field(default_factory=list)
    downstream_dependencies: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "service_topologies"
