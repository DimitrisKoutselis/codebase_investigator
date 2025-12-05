"""
Dependency Injection Configuration.

This module wires together all the concrete implementations
following Clean Architecture principles.
"""

from typing import Annotated, cast

from fastapi import Depends

from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.cache.redis_cache import RedisCacheService
from src.infrastructure.vector_store.faiss_store import FAISSVectorStore
from src.infrastructure.repositories.redis_session_repository import (
    RedisSessionRepository,
)
from src.infrastructure.repositories.redis_codebase_repository import (
    RedisCodebaseRepository,
)
from src.infrastructure.git.git_service import GitService
from src.infrastructure.mcp.client.mcp_client import MCPClientManager
from src.infrastructure.llm.graph.rag_graph import RAGGraph, create_rag_graph

from src.application.interfaces.i_cache_service import ICacheService
from src.application.interfaces.i_vector_store import IVectorStore
from src.application.interfaces.i_git_service import IGitService
from src.domain.repositories.i_chat_session_repository import IChatSessionRepository
from src.domain.repositories.i_codebase_repository import ICodebaseRepository

from src.application.use_cases.ingest_codebase import IngestCodebaseUseCase
from src.application.use_cases.send_message import SendMessageUseCase, IAgentRunner
from src.application.use_cases.get_session import GetSessionUseCase


# Settings
def get_app_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


# Cache Service
def get_cache_service(settings: SettingsDep) -> ICacheService:
    return RedisCacheService(
        redis_url=settings.redis_url,
        default_ttl=settings.redis_ttl_seconds,
    )


CacheServiceDep = Annotated[ICacheService, Depends(get_cache_service)]


# Vector Store
def get_vector_store(settings: SettingsDep) -> IVectorStore:
    return FAISSVectorStore(
        index_path=settings.faiss_index_path,
        gemini_api_key=settings.gemini_api_key,
    )


VectorStoreDep = Annotated[IVectorStore, Depends(get_vector_store)]


# Git Service
def get_git_service() -> IGitService:
    return GitService()


GitServiceDep = Annotated[IGitService, Depends(get_git_service)]


# MCP Client
def get_mcp_client() -> MCPClientManager:
    return MCPClientManager()


MCPClientDep = Annotated[MCPClientManager, Depends(get_mcp_client)]


# Repositories
def get_session_repository(settings: SettingsDep) -> IChatSessionRepository:
    return RedisSessionRepository(redis_url=settings.redis_url)


SessionRepositoryDep = Annotated[
    IChatSessionRepository, Depends(get_session_repository)
]


def get_codebase_repository(settings: SettingsDep) -> ICodebaseRepository:
    return RedisCodebaseRepository(redis_url=settings.redis_url)


CodebaseRepositoryDep = Annotated[ICodebaseRepository, Depends(get_codebase_repository)]


# RAG Graph
def get_rag_graph(
    vector_store: VectorStoreDep,
    mcp_client: MCPClientDep,
    settings: SettingsDep,
) -> RAGGraph:
    return create_rag_graph(
        vector_store=vector_store,
        mcp_client=mcp_client,
        gemini_api_key=settings.gemini_api_key,
    )


RAGGraphDep = Annotated[RAGGraph, Depends(get_rag_graph)]


# Use Cases
def get_ingest_use_case(
    codebase_repository: CodebaseRepositoryDep,
    git_service: GitServiceDep,
    vector_store: VectorStoreDep,
) -> IngestCodebaseUseCase:
    return IngestCodebaseUseCase(
        codebase_repository=codebase_repository,
        git_service=git_service,
        vector_store=vector_store,
    )


IngestUseCaseDep = Annotated[IngestCodebaseUseCase, Depends(get_ingest_use_case)]


def get_send_message_use_case(
    session_repository: SessionRepositoryDep,
    codebase_repository: CodebaseRepositoryDep,
    vector_store: VectorStoreDep,
    cache_service: CacheServiceDep,
    rag_graph: RAGGraphDep,
) -> SendMessageUseCase:
    return SendMessageUseCase(
        session_repository=session_repository,
        codebase_repository=codebase_repository,
        vector_store=vector_store,
        cache_service=cache_service,
        agent_runner=cast(IAgentRunner, rag_graph),
    )


SendMessageUseCaseDep = Annotated[
    SendMessageUseCase, Depends(get_send_message_use_case)
]


def get_session_use_case(
    session_repository: SessionRepositoryDep,
) -> GetSessionUseCase:
    return GetSessionUseCase(session_repository=session_repository)


GetSessionUseCaseDep = Annotated[GetSessionUseCase, Depends(get_session_use_case)]
