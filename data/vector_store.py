from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = Path(__file__).parent / "chroma"

EmbeddingFunction = Callable[[list[str]], list[list[float]]]


def default_embedding_function() -> embedding_functions.SentenceTransformerEmbeddingFunction:
    # 本地多语言模型，离线可用，首次调用会下载约 450MB 权重
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )


def get_client(persist_directory: str | Path = CHROMA_DIR) -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(persist_directory))


def get_collection(
    client: chromadb.ClientAPI,
    name: str,
    embedding_function: EmbeddingFunction | None = None,
) -> Any:
    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_function or default_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def upsert_texts(collection: Any, ids: list[str], texts: list[str]) -> None:
    collection.upsert(ids=ids, documents=texts)


def query_top_n(collection: Any, query_text: str, top_n: int) -> list[tuple[str, float]]:
    result = collection.query(query_texts=[query_text], n_results=top_n)
    ids = result["ids"][0]
    distances = result["distances"][0]
    # collection 用 cosine space 建的，distance = 1 - cosine_similarity
    return [(id_, 1.0 - distance) for id_, distance in zip(ids, distances)]


def get_embeddings(collection: Any, ids: list[str]) -> dict[str, list[float]]:
    if not ids:
        return {}
    result = collection.get(ids=ids, include=["embeddings"])
    return dict(zip(result["ids"], result["embeddings"]))


def embed_query(embedding_function: EmbeddingFunction, text: str) -> list[float]:
    return embedding_function([text])[0]
