import os
import pickle
from pathlib import Path
from typing import List, Any

import numpy as np
import faiss  # type: ignore[import-untyped]
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr

from src.application.interfaces.i_vector_store import (
    IVectorStore,
    CodeChunk,
    SearchResult,
)


class FAISSVectorStore(IVectorStore):
    """FAISS-based vector store implementation."""

    def __init__(
        self,
        index_path: str,
        gemini_api_key: str,
        embedding_model: str = "models/embedding-001",
    ):
        self._index_path = Path(index_path)
        self._index_path.mkdir(parents=True, exist_ok=True)

        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=SecretStr(gemini_api_key),
        )

        self._indexes: dict[str, Any] = {}
        self._chunks: dict[str, List[CodeChunk]] = {}

    def _get_index_file(self, codebase_id: str) -> Path:
        return self._index_path / f"{codebase_id}.faiss"

    def _get_chunks_file(self, codebase_id: str) -> Path:
        return self._index_path / f"{codebase_id}.chunks"

    async def create_index(self, codebase_id: str) -> None:
        """Create a new FAISS index for a codebase."""
        # Initialize empty index - will be populated when chunks are added
        self._indexes[codebase_id] = None
        self._chunks[codebase_id] = []

    async def add_chunks(self, codebase_id: str, chunks: List[CodeChunk]) -> None:
        """Add code chunks to the vector store."""
        if not chunks:
            return

        # Generate embeddings for all chunks
        texts = [chunk.content for chunk in chunks]
        embeddings = await self._embeddings.aembed_documents(texts)

        # Convert to numpy array
        embeddings_array = np.array(embeddings).astype("float32")

        # Create FAISS index
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)

        # Store index and chunks
        self._indexes[codebase_id] = index
        self._chunks[codebase_id] = chunks

        # Persist to disk
        faiss.write_index(index, str(self._get_index_file(codebase_id)))
        with open(self._get_chunks_file(codebase_id), "wb") as f:
            pickle.dump(chunks, f)

    async def search(
        self,
        codebase_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Search for relevant code chunks."""
        # Load index if not in memory
        if codebase_id not in self._indexes:
            index_file = self._get_index_file(codebase_id)
            chunks_file = self._get_chunks_file(codebase_id)

            if not index_file.exists():
                return []

            self._indexes[codebase_id] = faiss.read_index(str(index_file))
            with open(chunks_file, "rb") as f:
                self._chunks[codebase_id] = pickle.load(f)

        index = self._indexes[codebase_id]
        chunks = self._chunks[codebase_id]

        if index is None or not chunks:
            return []

        # Generate query embedding
        query_embedding = await self._embeddings.aembed_query(query)
        query_array = np.array([query_embedding]).astype("float32")

        # Search
        k = min(top_k, len(chunks))
        distances, indices = index.search(query_array, k)

        # Convert to results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(chunks):
                # Convert L2 distance to similarity score (inverse)
                score = 1 / (1 + distance)
                results.append(
                    SearchResult(
                        chunk=chunks[idx],
                        score=float(score),
                    )
                )

        return results

    async def delete_index(self, codebase_id: str) -> None:
        """Delete an index for a codebase."""
        # Remove from memory
        self._indexes.pop(codebase_id, None)
        self._chunks.pop(codebase_id, None)

        # Remove from disk
        index_file = self._get_index_file(codebase_id)
        chunks_file = self._get_chunks_file(codebase_id)

        if index_file.exists():
            os.remove(index_file)
        if chunks_file.exists():
            os.remove(chunks_file)
