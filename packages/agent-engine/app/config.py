"""
ResilienceAI Agent Engine — Configuration
Ports the JanShakti-AI config.py pattern using Pydantic BaseSettings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


class Settings(BaseSettings):
    # --- Server ---
    agent_engine_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:4000"

    # --- MongoDB ---
    mongo_uri: str = "mongodb://localhost:27017/resilienceai?replicaSet=rs0"
    mongo_db_name: str = "resilienceai"

    # --- Qdrant ---
    qdrant_uri: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "sre_runbooks"

    # --- LLM ---
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: str = "sk-your-key-here"
    llm_model: str = "gpt-4o-mini"

    # --- Embeddings ---
    embedding_api_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = "sk-your-key-here"
    embedding_model: str = "text-embedding-3-small"

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
