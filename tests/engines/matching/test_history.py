from decimal import Decimal

from engines.matching.history import format_campaign_context
from engines.matching.models import HistoricalCampaign


def _campaign(influencer_id: str = "INF001") -> HistoricalCampaign:
    return HistoricalCampaign(
        campaign_id="1",
        product_id="P001",
        influencer_id=influencer_id,
        campaign_date="2026-05-12",
        actual_gmv=Decimal("92000"),
        actual_roi=Decimal("3.4"),
        outcome_note="完播率高于均值",
    )


def test_format_campaign_context_none_returns_none() -> None:
    assert format_campaign_context(None, "INF001") is None


def test_format_campaign_context_same_influencer() -> None:
    result = format_campaign_context(_campaign("INF001"), "INF001")
    assert result == "该达人此前带过同类商品：GMV 92000 元、ROI 3.4——完播率高于均值"


def test_format_campaign_context_different_influencer() -> None:
    result = format_campaign_context(_campaign("INF005"), "INF001")
    assert result == "类似商品与相似达人风格的组合此前有过案例：GMV 92000 元、ROI 3.4——完播率高于均值"
