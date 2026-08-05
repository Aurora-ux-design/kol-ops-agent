from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from typing import Any

from data import db as data_db
from data import vector_store
from data.vector_store import EmbeddingFunction

from .formulas import cosine_similarity
from .models import InfluencerProfile, ProductProfile

INFLUENCER_AUDIENCE_COLLECTION = "influencer_audience"
INFLUENCER_STYLE_COLLECTION = "influencer_style"


def _row_to_influencer(row: sqlite3.Row) -> InfluencerProfile:
    return InfluencerProfile(
        influencer_id=row["influencer_id"],
        name=row["name"],
        category_tags=row["category_tags"],
        audience_profile=row["audience_profile"],
        content_style=row["content_style"],
        follower_count=row["follower_count"],
        historical_gmv_avg=Decimal(row["historical_gmv_avg"]),
        historical_roi_avg=Decimal(row["historical_roi_avg"]),
        historical_completion_rate=Decimal(row["historical_completion_rate"]),
        commission_rate_min=Decimal(row["commission_rate_min"]),
        commission_rate_max=Decimal(row["commission_rate_max"]),
        schedule_available_from=date.fromisoformat(row["schedule_available_from"]),
    )


def coarse_rank_influencers(
    conn: sqlite3.Connection,
    chroma_client: Any,
    product: ProductProfile,
    top_n: int = 30,
    embedding_function: EmbeddingFunction | None = None,
) -> list[tuple[InfluencerProfile, float, float]]:
    """按画像相似度选出 Top N 候选，同时算出每个候选的风格相似度。

    返回 (达人画像, 画像相似度, 风格相似度)，相似度是 [0,1] 的 cosine 值，
    还没转成 0-100 分——转分交给 formulas.semantic_similarity_to_score。
    """
    audience_collection = vector_store.get_collection(
        chroma_client, INFLUENCER_AUDIENCE_COLLECTION, embedding_function
    )
    style_collection = vector_store.get_collection(
        chroma_client, INFLUENCER_STYLE_COLLECTION, embedding_function
    )

    audience_matches = vector_store.query_top_n(audience_collection, product.target_audience, top_n)
    candidate_ids = [influencer_id for influencer_id, _ in audience_matches]
    audience_similarity = dict(audience_matches)

    style_vectors = vector_store.get_embeddings(style_collection, candidate_ids)
    style_embed_fn = embedding_function or vector_store.default_embedding_function()
    product_style_vector = vector_store.embed_query(style_embed_fn, product.tone)
    style_similarity = {
        influencer_id: cosine_similarity(product_style_vector, vector)
        for influencer_id, vector in style_vectors.items()
    }

    rows = data_db.get_influencers_by_ids(conn, candidate_ids)
    influencers_by_id = {row["influencer_id"]: _row_to_influencer(row) for row in rows}

    return [
        (
            influencers_by_id[influencer_id],
            audience_similarity[influencer_id],
            style_similarity[influencer_id],
        )
        for influencer_id in candidate_ids
        if influencer_id in influencers_by_id
    ]
