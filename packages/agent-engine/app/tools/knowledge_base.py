"""
ResilienceAI — Knowledge Base Tool
Queries Qdrant for semantically similar SRE runbooks and post-mortems.
Now with full OpenAI embedding generation and Qdrant vector search.
"""

from pydantic import BaseModel, Field
from typing import Optional
from langchain_openai import OpenAIEmbeddings
from app.lib.qdrant import get_qdrant_client
from app.config import settings
from qdrant_client.models import Filter, FieldCondition, MatchValue


class KnowledgeBaseInput(BaseModel):
    query: str = Field(description="Natural language description of the incident or error signature")
    target_service: str = Field(description="Service name to filter runbooks by")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


class RunbookMatch(BaseModel):
    runbook_id: str
    title: str
    content: str
    score: float


class KnowledgeBaseOutput(BaseModel):
    matches: list[RunbookMatch]
    query_used: str


_embeddings_client: Optional[OpenAIEmbeddings] = None


def _get_embeddings() -> OpenAIEmbeddings:
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.embedding_api_key,
            openai_api_base=settings.embedding_api_url,
        )
    return _embeddings_client


async def query_knowledge_base(
    query: str,
    target_service: str,
    top_k: int = 5,
) -> KnowledgeBaseOutput:
    """Query Qdrant for semantically similar runbooks and historical post-mortems.

    1. Generates an embedding vector for the query via OpenAI
    2. Searches Qdrant with a payload filter on targetService
    3. Returns top-K semantically similar runbooks with relevance scores

    Args:
        query: Natural language description of the incident.
        target_service: Service name to limit results to.
        top_k: Number of results to return.

    Returns:
        KnowledgeBaseOutput with ranked runbook matches.
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    # Generate embedding vector
    embeddings = _get_embeddings()
    query_vector = embeddings.embed_query(query[:2000])  # Cap query length for embedding

    # Search Qdrant with service filter
    search_filter = Filter(
        must=[
            FieldCondition(
                key="target_service",
                match=MatchValue(value=target_service),
            )
        ]
    )

    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        query_filter=search_filter,
        limit=top_k,
        with_payload=True,
        score_threshold=0.3,
    )

    matches = [
        RunbookMatch(
            runbook_id=str(r.id),
            title=r.payload.get("title", "Untitled Runbook") if r.payload else "Untitled Runbook",
            content=r.payload.get("content", "")[:2000] if r.payload else "",
            score=round(float(r.score), 4),
        )
        for r in results
    ]

    return KnowledgeBaseOutput(matches=matches, query_used=query[:500])
