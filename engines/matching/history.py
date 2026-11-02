from __future__ import annotations

import sqlite3
from contextlib import closing
from decimal import Decimal

from data import db as data_db
from data import vector_store
from data.vector_store import EmbeddingFunction

from .models import HistoricalCampaign, InfluencerProfile, ProductProfile

CAMPAIGN_COLLECTION = "historical_campaigns"


def _row_to_campaign(row: sqlite3.Row) -> HistoricalCampaign:
    return HistoricalCampaign(
        campaign_id=str(row["id"]),
        product_id=row["product_id"],
        influencer_id=row["influencer_id"],
        campaign_date=row["campaign_date"],
        actual_gmv=Decimal(row["actual_gmv"]),
        actual_roi=Decimal(row["actual_roi"]),
        outcome_note=row["outcome_note"],
    )


def retrieve_similar_campaign(
    product: ProductProfile,
    influencer: InfluencerProfile,
    embedding_function: EmbeddingFunction | None = None,
) -> HistoricalCampaign | None:
    """按商品类目/调性 + 达人内容风格去检索最相关的一条历史合作记录。

    检索范围是全部历史合作案例，不是只查这个达人自己的——所以命中的可能是这个达人自己
    的过往案例，也可能是别的达人在类似商品/风格组合上的案例，两种都有参考价值。
    """
    client = vector_store.get_client()
    collection = vector_store.get_collection(client, CAMPAIGN_COLLECTION, embedding_function)
    if collection.count() == 0:
        return None

    query_text = f"{product.category} {product.tone} {influencer.content_style}"
    matches = vector_store.query_top_n(collection, query_text, top_n=1)
    if not matches:
        return None

    campaign_id, _ = matches[0]
    with closing(data_db.get_connection()) as conn:
        row = data_db.get_historical_campaign(conn, campaign_id)
    return _row_to_campaign(row)


def format_campaign_context(campaign: HistoricalCampaign | None, influencer_id: str) -> str | None:
    if campaign is None:
        return None
    subject = "该达人此前带过同类商品" if campaign.influencer_id == influencer_id else "类似商品与相似达人风格的组合此前有过案例"
    return f"{subject}：GMV {campaign.actual_gmv} 元、ROI {campaign.actual_roi}——{campaign.outcome_note}"
