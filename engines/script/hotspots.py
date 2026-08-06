from __future__ import annotations

import sqlite3
from contextlib import closing

from data import db as data_db
from data import vector_store
from data.vector_store import EmbeddingFunction
from engines.matching.models import InfluencerProfile, ProductProfile

from .models import HotspotEntry

HOTSPOT_COLLECTION = "hotspots"


def _row_to_hotspot(row: sqlite3.Row) -> HotspotEntry:
    return HotspotEntry(
        hotspot_id=str(row["id"]),
        keyword=row["keyword"],
        description=row["description"],
        is_enabled=bool(row["is_enabled"]),
        created_at=row["created_at"],
    )


def _sync_chroma(entry: HotspotEntry, embedding_function: EmbeddingFunction | None = None) -> None:
    # Chroma 的 hotspots collection 只镜像"已启用"的条目，禁用时直接从 Chroma 摘除，
    # 这样检索阶段不用额外做 is_enabled 的 metadata 过滤
    client = vector_store.get_client()
    collection = vector_store.get_collection(client, HOTSPOT_COLLECTION, embedding_function)
    if entry.is_enabled:
        vector_store.upsert_texts(
            collection, [entry.hotspot_id], [f"{entry.keyword} {entry.description}"]
        )
    else:
        vector_store.delete_texts(collection, [entry.hotspot_id])


def create_hotspot(
    keyword: str, description: str, embedding_function: EmbeddingFunction | None = None
) -> HotspotEntry:
    with closing(data_db.get_connection()) as conn:
        hotspot_id = data_db.create_hotspot(conn, keyword, description)
        row = data_db.get_hotspot(conn, hotspot_id)
    entry = _row_to_hotspot(row)
    _sync_chroma(entry, embedding_function)
    return entry


def set_hotspot_enabled(
    hotspot_id: str, enabled: bool, embedding_function: EmbeddingFunction | None = None
) -> None:
    with closing(data_db.get_connection()) as conn:
        data_db.set_hotspot_enabled(conn, hotspot_id, enabled)
        row = data_db.get_hotspot(conn, hotspot_id)
    entry = _row_to_hotspot(row)
    _sync_chroma(entry, embedding_function)


def list_hotspots() -> list[HotspotEntry]:
    with closing(data_db.get_connection()) as conn:
        rows = data_db.get_all_hotspots(conn)
    return [_row_to_hotspot(row) for row in rows]


def retrieve_relevant_hotspots(
    product: ProductProfile,
    influencer: InfluencerProfile,
    top_n: int = 2,
    embedding_function: EmbeddingFunction | None = None,
) -> list[HotspotEntry]:
    client = vector_store.get_client()
    collection = vector_store.get_collection(client, HOTSPOT_COLLECTION, embedding_function)
    if collection.count() == 0:
        return []

    query_text = f"{product.category} {product.tone} {influencer.content_style}"
    matches = vector_store.query_top_n(collection, query_text, top_n)
    if not matches:
        return []

    ids = [hotspot_id for hotspot_id, _ in matches]
    with closing(data_db.get_connection()) as conn:
        rows = [data_db.get_hotspot(conn, hotspot_id) for hotspot_id in ids]
    return [_row_to_hotspot(row) for row in rows]


def format_hotspot_context(hotspots: list[HotspotEntry]) -> str | None:
    if not hotspots:
        return None
    return "；".join(f"{h.keyword}——{h.description}" for h in hotspots)
