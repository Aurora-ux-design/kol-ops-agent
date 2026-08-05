import json
import sqlite3

import pytest

from data.db import (
    get_influencers_by_ids,
    get_product,
    init_db,
    record_match,
    upsert_influencers,
    upsert_products,
)


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    init_db(connection)
    return connection


def _influencer_row(influencer_id: str = "INF001") -> dict:
    return {
        "influencer_id": influencer_id,
        "name": "小美的美妆日记",
        "category_tags": "美妆、护肤",
        "audience_profile": "18-25岁女性",
        "content_style": "幽默口播",
        "follower_count": 320000,
        "historical_gmv_avg": "85000",
        "historical_roi_avg": "3.2",
        "historical_completion_rate": "0.32",
        "commission_rate_min": "0.20",
        "commission_rate_max": "0.35",
        "schedule_available_from": "2026-08-05",
    }


def _product_row(product_id: str = "P001") -> dict:
    return {
        "product_id": product_id,
        "name": "清透水感面膜",
        "category": "美妆",
        "target_audience": "18-25岁女性",
        "tone": "性价比种草",
        "selling_price": "99",
        "purchase_cost": "35",
        "packaging_fee": "3",
        "logistics_fee": "5",
        "overhead_fee": "2",
        "platform_tech_fee": "3",
        "tax": "2",
        "platform_commission_rate": "0.05",
    }


def test_init_db_creates_expected_tables(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert {"influencer_pool", "product_catalog", "match_records"} <= tables


def test_upsert_and_get_influencers_by_ids(conn: sqlite3.Connection) -> None:
    upsert_influencers(conn, [_influencer_row("INF001"), _influencer_row("INF002")])

    rows = get_influencers_by_ids(conn, ["INF001", "INF002"])

    assert {row["influencer_id"] for row in rows} == {"INF001", "INF002"}


def test_get_influencers_by_ids_empty_list_returns_empty(conn: sqlite3.Connection) -> None:
    assert get_influencers_by_ids(conn, []) == []


def test_upsert_influencers_updates_existing_row(conn: sqlite3.Connection) -> None:
    upsert_influencers(conn, [_influencer_row("INF001")])
    updated = _influencer_row("INF001")
    updated["name"] = "改名后的达人"
    upsert_influencers(conn, [updated])

    rows = get_influencers_by_ids(conn, ["INF001"])

    assert len(rows) == 1
    assert rows[0]["name"] == "改名后的达人"


def test_upsert_and_get_product(conn: sqlite3.Connection) -> None:
    upsert_products(conn, [_product_row("P001")])

    row = get_product(conn, "P001")

    assert row["name"] == "清透水感面膜"
    assert row["selling_price"] == "99"


def test_get_product_missing_raises_key_error(conn: sqlite3.Connection) -> None:
    with pytest.raises(KeyError):
        get_product(conn, "NOT_EXIST")


def test_record_match_persists_snapshot(conn: sqlite3.Connection) -> None:
    record_match(
        conn,
        product_id="P001",
        requested_date="2026-08-10",
        weights_snapshot={"audience_overlap": "0.25"},
        candidates_snapshot=[{"influencer_id": "INF001", "weighted_total": "88.5"}],
    )

    row = conn.execute("SELECT * FROM match_records").fetchone()

    assert row["product_id"] == "P001"
    assert json.loads(row["weights_snapshot"]) == {"audience_overlap": "0.25"}
    assert json.loads(row["candidates_snapshot"])[0]["influencer_id"] == "INF001"
    assert row["acceptance_status"] is None
