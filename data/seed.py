"""一次性初始化脚本：读 data/mock/*.csv，写入 SQLite + ChromaDB。用法：python -m data.seed"""

from __future__ import annotations

import csv
from pathlib import Path

from data import db, vector_store

MOCK_DIR = Path(__file__).parent / "mock"


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed() -> None:
    influencer_rows = _read_csv(MOCK_DIR / "influencers.csv")
    product_rows = _read_csv(MOCK_DIR / "products.csv")
    hotspot_rows = _read_csv(MOCK_DIR / "hotspots.csv")

    conn = db.get_connection()
    db.init_db(conn)
    db.upsert_influencers(conn, influencer_rows)
    db.upsert_products(conn, product_rows)

    client = vector_store.get_client()
    audience_collection = vector_store.get_collection(client, "influencer_audience")
    style_collection = vector_store.get_collection(client, "influencer_style")

    ids = [row["influencer_id"] for row in influencer_rows]
    audience_texts = [row["audience_profile"] for row in influencer_rows]
    style_texts = [row["content_style"] for row in influencer_rows]

    vector_store.upsert_texts(audience_collection, ids, audience_texts)
    vector_store.upsert_texts(style_collection, ids, style_texts)

    # 热点没有像达人/商品那样天然的业务主键（id 是自增的），按关键词去重，
    # 这样重复跑 seed 不会插入重复条目，也不会碰运营已经在热点库页面手动加的条目
    existing_keywords = {row["keyword"] for row in db.get_all_hotspots(conn)}
    new_hotspot_rows = [row for row in hotspot_rows if row["keyword"] not in existing_keywords]
    if new_hotspot_rows:
        hotspot_collection = vector_store.get_collection(client, "hotspots")
        hotspot_ids = [
            str(db.create_hotspot(conn, row["keyword"], row["description"]))
            for row in new_hotspot_rows
        ]
        hotspot_texts = [f"{row['keyword']} {row['description']}" for row in new_hotspot_rows]
        vector_store.upsert_texts(hotspot_collection, hotspot_ids, hotspot_texts)

    print(
        f"已写入 {len(influencer_rows)} 个达人、{len(product_rows)} 个商品、"
        f"{len(new_hotspot_rows)} 条新热点，并生成 embedding。"
    )


if __name__ == "__main__":
    seed()
