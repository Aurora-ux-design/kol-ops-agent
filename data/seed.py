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

    print(f"已写入 {len(influencer_rows)} 个达人、{len(product_rows)} 个商品，并生成 embedding。")


if __name__ == "__main__":
    seed()
