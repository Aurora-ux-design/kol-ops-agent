from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engines.profit import CostStructure
from engines.profit.nl_query import (
    ExtractedQueryParams,
    QueryIntent,
    answer_breakeven_query,
    answer_net_profit_query,
    extract_query_params,
)

SELLING_PRICE = Decimal("200")
PLATFORM_COMMISSION_RATE = Decimal("0.05")


@pytest.fixture
def cost_structure() -> CostStructure:
    return CostStructure(
        purchase_cost=Decimal("80"),
        packaging_fee=Decimal("5"),
        logistics_fee=Decimal("8"),
        overhead_fee=Decimal("2"),
        platform_tech_fee=Decimal("3"),
        tax=Decimal("2"),
    )


def _tool_use_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=payload)])


def _text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def test_extract_query_params_net_profit() -> None:
    mocked_response = _tool_use_response(
        {"intent": "net_profit", "selling_price": 199, "influencer_commission_rate": 0.3}
    )
    with patch("engines.profit.nl_query.create_message", return_value=mocked_response) as mock_call:
        params = extract_query_params("这个商品卖 199，给达人 30% 佣金还能赚多少？")

    assert params.intent is QueryIntent.NET_PROFIT
    assert params.selling_price == Decimal("199")
    assert params.influencer_commission_rate == Decimal("0.3")
    mock_call.assert_called_once()


def test_extract_query_params_breakeven() -> None:
    mocked_response = _tool_use_response(
        {"intent": "breakeven", "selling_price": 199, "influencer_commission_rate": None}
    )
    with patch("engines.profit.nl_query.create_message", return_value=mocked_response):
        params = extract_query_params("佣金给到多少还能保本？")

    assert params.intent is QueryIntent.BREAKEVEN
    assert params.influencer_commission_rate is None


def test_extract_query_params_rejects_missing_rate_for_net_profit() -> None:
    mocked_response = _tool_use_response(
        {"intent": "net_profit", "selling_price": 199, "influencer_commission_rate": None}
    )
    with patch("engines.profit.nl_query.create_message", return_value=mocked_response):
        with pytest.raises(ValueError):
            extract_query_params("卖 199 能赚多少？")


def test_answer_net_profit_query_uses_deterministic_calculation(cost_structure: CostStructure) -> None:
    params = ExtractedQueryParams(
        intent=QueryIntent.NET_PROFIT,
        selling_price=SELLING_PRICE,
        influencer_commission_rate=Decimal("0.3"),
    )
    with patch(
        "engines.profit.nl_query.create_message", return_value=_text_response("净利润约 30 元。")
    ) as mock_call:
        result, explanation = answer_net_profit_query(
            "卖 200 给 30% 佣金还能赚多少？", params, cost_structure, PLATFORM_COMMISSION_RATE
        )

    # 数值必须来自 calculate_profit，不是 LLM 编的
    assert result.net_profit == Decimal("30")
    assert result.roi == Decimal("200") / Decimal("170")
    assert explanation == "净利润约 30 元。"

    prompt_content = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "30.00 元" in prompt_content
    assert "15.00%" in prompt_content  # 保本佣金率 0.45 - 已用佣金率 0.30 = 0.15


def test_answer_net_profit_query_rejects_wrong_intent(cost_structure: CostStructure) -> None:
    params = ExtractedQueryParams(
        intent=QueryIntent.BREAKEVEN, selling_price=SELLING_PRICE, influencer_commission_rate=None
    )
    with pytest.raises(ValueError):
        answer_net_profit_query("...", params, cost_structure, PLATFORM_COMMISSION_RATE)


def test_answer_breakeven_query_uses_deterministic_calculation(cost_structure: CostStructure) -> None:
    params = ExtractedQueryParams(
        intent=QueryIntent.BREAKEVEN, selling_price=SELLING_PRICE, influencer_commission_rate=None
    )
    with patch(
        "engines.profit.nl_query.create_message", return_value=_text_response("保本佣金率是 45%。")
    ) as mock_call:
        breakeven_rate, explanation = answer_breakeven_query(
            "佣金给到多少还能保本？", params, cost_structure, PLATFORM_COMMISSION_RATE
        )

    assert breakeven_rate == Decimal("0.45")
    assert explanation == "保本佣金率是 45%。"

    prompt_content = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "45.00%" in prompt_content


def test_answer_breakeven_query_rejects_wrong_intent(cost_structure: CostStructure) -> None:
    params = ExtractedQueryParams(
        intent=QueryIntent.NET_PROFIT,
        selling_price=SELLING_PRICE,
        influencer_commission_rate=Decimal("0.3"),
    )
    with pytest.raises(ValueError):
        answer_breakeven_query("...", params, cost_structure, PLATFORM_COMMISSION_RATE)
