from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from engines.matching.models import InfluencerProfile, ProductProfile
from engines.profit import CostStructure
from engines.script.generate import (
    generate_narrative_sections,
    generate_review_sections,
    generate_voiceover_sections,
)


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


def _influencer() -> InfluencerProfile:
    return InfluencerProfile(
        influencer_id="INF001",
        name="小美的美妆日记",
        category_tags="美妆、护肤",
        audience_profile="18-25岁女性为主、注重性价比",
        content_style="幽默口播、快节奏种草",
        follower_count=320000,
        historical_gmv_avg=Decimal("85000"),
        historical_roi_avg=Decimal("3.2"),
        historical_completion_rate=Decimal("0.32"),
        commission_rate_min=Decimal("0.20"),
        commission_rate_max=Decimal("0.35"),
        schedule_available_from=date(2026, 8, 5),
    )


def test_generate_voiceover_sections_returns_parsed_tool_input() -> None:
    payload = {
        "hook": "钩子",
        "pain_point": "痛点",
        "selling_points": ["卖点1", "卖点2"],
        "call_to_action": "下单",
        "applicable_scenario": "适合场景",
        "hotspot_reference": "",
    }
    with patch(
        "engines.script.generate.create_message", return_value=_tool_use_response(payload)
    ) as mock_call:
        result = generate_voiceover_sections(_product(), _influencer(), target_seconds=20)

    assert result == payload
    prompt_content = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "幽默口播、快节奏种草" in prompt_content
    assert "约 20 秒" in prompt_content


def test_generate_voiceover_sections_returns_hotspot_reference_when_used() -> None:
    payload = {
        "hook": "钩子",
        "pain_point": "痛点",
        "selling_points": ["卖点1"],
        "call_to_action": "下单",
        "applicable_scenario": "适合场景",
        "hotspot_reference": "秋天的第一杯奶茶",
    }
    with patch("engines.script.generate.create_message", return_value=_tool_use_response(payload)):
        result = generate_voiceover_sections(
            _product(), _influencer(), hotspot_context="秋天的第一杯奶茶——情感共鸣类 Hook"
        )

    assert result["hotspot_reference"] == "秋天的第一杯奶茶"


def test_generate_voiceover_sections_coerces_json_array_string_selling_points() -> None:
    # DeepSeek 偶尔把数组字段整个吐成字符串，比如 '["卖点1","卖点2"]' 而不是真正的数组
    payload = {
        "hook": "钩子",
        "pain_point": "痛点",
        "selling_points": '["卖点1", "卖点2"]',
        "call_to_action": "下单",
        "applicable_scenario": "适合场景",
    }
    with patch("engines.script.generate.create_message", return_value=_tool_use_response(payload)):
        result = generate_voiceover_sections(_product(), _influencer())

    assert result["selling_points"] == ["卖点1", "卖点2"]


def test_generate_voiceover_sections_wraps_plain_string_selling_points() -> None:
    payload = {
        "hook": "钩子",
        "pain_point": "痛点",
        "selling_points": "不是数组也不是json的一整段话",
        "call_to_action": "下单",
        "applicable_scenario": "适合场景",
    }
    with patch("engines.script.generate.create_message", return_value=_tool_use_response(payload)):
        result = generate_voiceover_sections(_product(), _influencer())

    assert result["selling_points"] == ["不是数组也不是json的一整段话"]


def test_generate_narrative_sections_returns_parsed_tool_input() -> None:
    payload = {
        "scene_setup": "铺垫",
        "product_integration": "植入",
        "emotional_turn": "转折",
        "closing": "收尾",
        "applicable_scenario": "适合场景",
    }
    with patch("engines.script.generate.create_message", return_value=_tool_use_response(payload)):
        result = generate_narrative_sections(_product(), _influencer())

    assert result == payload


def test_generate_review_sections_returns_parsed_tool_input() -> None:
    payload = {
        "unboxing": "开箱",
        "trial_comparison": "对比",
        "verdict": "结论",
        "applicable_scenario": "适合场景",
    }
    with patch("engines.script.generate.create_message", return_value=_tool_use_response(payload)):
        result = generate_review_sections(_product(), _influencer())

    assert result == payload


def test_generate_voiceover_sections_includes_hotspot_context_when_given() -> None:
    payload = {
        "hook": "钩子",
        "pain_point": "痛点",
        "selling_points": ["卖点1"],
        "call_to_action": "下单",
        "applicable_scenario": "适合场景",
    }
    with patch(
        "engines.script.generate.create_message", return_value=_tool_use_response(payload)
    ) as mock_call:
        generate_voiceover_sections(_product(), _influencer(), hotspot_context="秋天的第一杯奶茶梗")

    prompt_content = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "秋天的第一杯奶茶梗" in prompt_content
