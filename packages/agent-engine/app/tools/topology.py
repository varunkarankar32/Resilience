"""
ResilienceAI — Topology Tool
Fetches microservice upstream/downstream dependency lists from MongoDB.
"""

from typing import Literal
from pydantic import BaseModel, Field
from app.models.service_topology import ServiceTopology


class TopologyInput(BaseModel):
    service_name: str = Field(description="Name of the microservice to query topology for")


class TopologyOutput(BaseModel):
    service_name: str
    upstream: list[str]
    downstream: list[str]
    found: bool


async def fetch_topology(service_name: str) -> TopologyOutput:
    """Query MongoDB for a service's upstream and downstream dependencies.

    This tool maps the blast-radius of an incident by pulling the dependency
    graph for the affected microservice. Used by the LangGraph Router LLM to
    determine which services may be impacted.

    Args:
        service_name: The microservice name (e.g., "payment-service").

    Returns:
        TopologyOutput with upstream/downstream lists or empty lists if not found.
    """
    topology = await ServiceTopology.find_one(
        ServiceTopology.service_name == service_name
    )

    if topology is None:
        return TopologyOutput(
            service_name=service_name,
            upstream=[],
            downstream=[],
            found=False,
        )

    return TopologyOutput(
        service_name=topology.service_name,
        upstream=topology.upstream_dependencies,
        downstream=topology.downstream_dependencies,
        found=True,
    )
