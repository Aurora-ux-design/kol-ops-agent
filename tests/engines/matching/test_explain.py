from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from engines.matching.explain import explain_matches
from engines.matching.models import DimensionScore, MatchCandidate, ProductProfile
from engines.profit import CostStructure


def _tool_use_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=payload)])


def _product() -> ProductProfile:
    return ProductProfile(
        product_id="P001",
        name="清透水感面膜",
        category="美妆",
        target_audience="18-25岁女性",
        tone="性价比种草",
        selling_price=Decimal("99"),
        cost_structure=CostStructure(
            purchase_cost=Decimal("35"),
            packaging_fee=Decimal("3"),
            logistics_fee=Decimal("5"),
            overhead_fee=Decimal("2"),
            platform_tech_fee=Decimal("3"),
            tax=Decimal("2"),
        ),
        platform_commission_rate=Decimal("0.05"),
    )


def _candidate(influencer_id: str) -> MatchCandidate:
    return MatchCandidate(
        influencer_id=influencer_id,
        dimension_scores=(
            DimensionScore(name="audience_overlap", score=Decimal("82"), detail="画像相似度 0.82"),
            DimensionScore(name="historical_performance", score=Decimal("60"), detail="候选池内排名靠前"),
        ),
        weighted_total=Decimal("75.5"),
    )


def test_explain_matches_maps_reasons_by_influencer_id() -> None:
    mocked_response = _tool_use_response(
        {
            "reasons": [
                {"influencer_id": "INF001", "reason": "画像重合度高，历史表现也不错。"},
                {"influencer_id": "INF002", "reason": "档期最快，但历史表现一般。"},
            ]
        }
    )
    with patch("engines.matching.explain.create_message", return_value=mocked_response) as mock_call:
        reasons = explain_matches(_product(), [_candidate("INF001"), _candidate("INF002")])

    assert reasons == {
        "INF001": "画像重合度高，历史表现也不错。",
        "INF002": "档期最快，但历史表现一般。",
    }
    mock_call.assert_called_once()


def test_explain_matches_prompt_contains_exact_scores() -> None:
    mocked_response = _tool_use_response({"reasons": [{"influencer_id": "INF001", "reason": "x"}]})
    with patch("engines.matching.explain.create_message", return_value=mocked_response) as mock_call:
        explain_matches(_product(), [_candidate("INF001")])

    prompt_content = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "82.0 分" in prompt_content
    assert "75.5" in prompt_content
