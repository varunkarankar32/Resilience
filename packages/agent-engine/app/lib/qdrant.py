"""
ResilienceAI Agent Engine — Qdrant Client
Wrapper around Qdrant for semantic runbook search.
"""

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from app.config import settings

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client."""
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_uri,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
        )
    return _client


async def init_qdrant() -> None:
    """Initialize Qdrant collection for SRE runbooks."""
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        client.get_collection(collection_name)
        print(f"[Qdrant] Collection '{collection_name}' already exists")
    except (UnexpectedResponse, Exception):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1536,  # text-embedding-3-small dimension
                distance=models.Distance.COSINE,
            ),
        )
        print(f"[Qdrant] Collection '{collection_name}' created")


async def close_qdrant() -> None:
    """Close Qdrant client connection."""
    global _client
    if _client:
        _client.close()
        _client = None
        print("[Qdrant] Client closed")
