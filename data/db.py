from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

# data/ 是数据层，位于 engines/ 之下，这里只处理原始行（dict/sqlite3.Row），
# 不引用 engines.* 里的 dataclass —— 避免 data 反向依赖 engines 造成循环导入。
# dict/Row 到 InfluencerProfile/ProductProfile 等 dataclass 的转换放在 engines/matching 里做。

DB_PATH = Path(__file__).parent / "kol_ops.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS influencer_pool (
    influencer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category_tags TEXT NOT NULL,
    audience_profile TEXT NOT NULL,
    content_style TEXT NOT NULL,
    follower_count INTEGER NOT NULL,
    historical_gmv_avg TEXT NOT NULL,
    historical_roi_avg TEXT NOT NULL,
    historical_completion_rate TEXT NOT NULL,
    commission_rate_min TEXT NOT NULL,
    commission_rate_max TEXT NOT NULL,
    schedule_available_from TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_catalog (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    target_audience TEXT NOT NULL,
    tone TEXT NOT NULL,
    selling_price TEXT NOT NULL,
    purchase_cost TEXT NOT NULL,
    packaging_fee TEXT NOT NULL,
    logistics_fee TEXT NOT NULL,
    overhead_fee TEXT NOT NULL,
    platform_tech_fee TEXT NOT NULL,
    tax TEXT NOT NULL,
    platform_commission_rate TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS match_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    product_id TEXT NOT NULL,
    requested_date TEXT NOT NULL,
    weights_snapshot TEXT NOT NULL,
    candidates_snapshot TEXT NOT NULL,
    acceptance_status TEXT,
    actual_gmv TEXT,
    actual_roi TEXT
);

CREATE TABLE IF NOT EXISTS hotspots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    description TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    source_url TEXT,
    raw_note TEXT
);
"""

# hotspots 表后来加了 source_url/raw_note 两列。CREATE TABLE IF NOT EXISTS 对已经存在的表不生效，
# 已经 seed 过的本地/云端数据库要靠这个显式迁移把新列补上，不会丢已有数据
_HOTSPOT_MIGRATION_COLUMNS = {
    "source_url": "TEXT",
    "raw_note": "TEXT",
}


def _migrate_hotspots_columns(conn: sqlite3.Connection) -> None:
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(hotspots)").fetchall()}
    for column, column_type in _HOTSPOT_MIGRATION_COLUMNS.items():
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE hotspots ADD COLUMN {column} {column_type}")
    conn.commit()


_INFLUENCER_COLUMNS = [
    "influencer_id",
    "name",
    "category_tags",
    "audience_profile",
    "content_style",
    "follower_count",
    "historical_gmv_avg",
    "historical_roi_avg",
    "historical_completion_rate",
    "commission_rate_min",
    "commission_rate_max",
    "schedule_available_from",
]

_PRODUCT_COLUMNS = [
    "product_id",
    "name",
    "category",
    "target_audience",
    "tone",
    "selling_price",
    "purchase_cost",
    "packaging_fee",
    "logistics_fee",
    "overhead_fee",
    "platform_tech_fee",
    "tax",
    "platform_commission_rate",
]


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
    _migrate_hotspots_columns(conn)


def upsert_influencers(conn: sqlite3.Connection, rows: list[dict]) -> None:
    placeholders = ", ".join("?" for _ in _INFLUENCER_COLUMNS)
    update_clause = ", ".join(f"{col}=excluded.{col}" for col in _INFLUENCER_COLUMNS[1:])
    conn.executemany(
        f"""
        INSERT INTO influencer_pool ({", ".join(_INFLUENCER_COLUMNS)}) VALUES ({placeholders})
        ON CONFLICT(influencer_id) DO UPDATE SET {update_clause}
        """,
        [tuple(row[col] for col in _INFLUENCER_COLUMNS) for row in rows],
    )
    conn.commit()


def get_influencers_by_ids(conn: sqlite3.Connection, influencer_ids: list[str]) -> list[sqlite3.Row]:
    if not influencer_ids:
        return []
    placeholders = ",".join("?" for _ in influencer_ids)
    return conn.execute(
        f"SELECT * FROM influencer_pool WHERE influencer_id IN ({placeholders})", influencer_ids
    ).fetchall()


def get_influencer(conn: sqlite3.Connection, influencer_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM influencer_pool WHERE influencer_id = ?", (influencer_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"未找到达人：{influencer_id}")
    return row


def get_all_influencers(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM influencer_pool ORDER BY influencer_id").fetchall()


def upsert_products(conn: sqlite3.Connection, rows: list[dict]) -> None:
    placeholders = ", ".join("?" for _ in _PRODUCT_COLUMNS)
    update_clause = ", ".join(f"{col}=excluded.{col}" for col in _PRODUCT_COLUMNS[1:])
    conn.executemany(
        f"""
        INSERT INTO product_catalog ({", ".join(_PRODUCT_COLUMNS)}) VALUES ({placeholders})
        ON CONFLICT(product_id) DO UPDATE SET {update_clause}
        """,
        [tuple(row[col] for col in _PRODUCT_COLUMNS) for row in rows],
    )
    conn.commit()


def get_product(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM product_catalog WHERE product_id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"未找到商品：{product_id}")
    return row


def get_all_products(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM product_catalog ORDER BY product_id").fetchall()


def create_hotspot(
    conn: sqlite3.Connection,
    keyword: str,
    description: str,
    source_url: str | None = None,
    raw_note: str | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO hotspots (keyword, description, is_enabled, created_at, source_url, raw_note)
        VALUES (?, ?, 1, ?, ?, ?)
        """,
        (keyword, description, datetime.now().isoformat(), source_url, raw_note),
    )
    conn.commit()
    return cursor.lastrowid


def get_hotspot(conn: sqlite3.Connection, hotspot_id: int | str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM hotspots WHERE id = ?", (hotspot_id,)).fetchone()
    if row is None:
        raise KeyError(f"未找到热点：{hotspot_id}")
    return row


def get_all_hotspots(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM hotspots ORDER BY created_at DESC").fetchall()


def set_hotspot_enabled(conn: sqlite3.Connection, hotspot_id: int | str, enabled: bool) -> None:
    conn.execute("UPDATE hotspots SET is_enabled = ? WHERE id = ?", (1 if enabled else 0, hotspot_id))
    conn.commit()


def record_match(
    conn: sqlite3.Connection,
    product_id: str,
    requested_date: str,
    weights_snapshot: dict,
    candidates_snapshot: list[dict],
) -> None:
    conn.execute(
        """
        INSERT INTO match_records (
            created_at, product_id, requested_date, weights_snapshot, candidates_snapshot,
            acceptance_status, actual_gmv, actual_roi
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
        """,
        (
            datetime.now().isoformat(),
            product_id,
            requested_date,
            json.dumps(weights_snapshot, default=str, ensure_ascii=False),
            json.dumps(candidates_snapshot, default=str, ensure_ascii=False),
        ),
    )
    conn.commit()
