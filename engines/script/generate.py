from __future__ import annotations

import json

from integrations.llm_client import create_message

from engines.matching.models import InfluencerProfile, ProductProfile

_VOICEOVER_TOOL_NAME = "write_voiceover_script"
_NARRATIVE_TOOL_NAME = "write_narrative_script"
_REVIEW_TOOL_NAME = "write_review_script"

_VOICEOVER_TOOL = {
    "name": _VOICEOVER_TOOL_NAME,
    "description": "写一版口播带货脚本",
    "input_schema": {
        "type": "object",
        "properties": {
            "hook": {"type": "string", "description": "开头 3 秒抓注意力的钩子"},
            "pain_point": {"type": "string", "description": "痛点引入"},
            "selling_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "卖点罗列，2~4 条",
            },
            "call_to_action": {"type": "string", "description": "促单话术"},
            "applicable_scenario": {"type": "string", "description": "这版脚本适合什么场景/什么风格的达人来讲"},
            "hotspot_reference": {
                "type": "string",
                "description": "如果用到了给定的热点参考，写出具体是哪一个；没有热点参考或者没用到就留空字符串",
            },
        },
        "required": ["hook", "pain_point", "selling_points", "call_to_action", "applicable_scenario"],
    },
}

_NARRATIVE_TOOL = {
    "name": _NARRATIVE_TOOL_NAME,
    "description": "写一版剧情带货脚本",
    "input_schema": {
        "type": "object",
        "properties": {
            "scene_setup": {"type": "string", "description": "场景铺垫"},
            "product_integration": {"type": "string", "description": "商品作为解决方案自然植入"},
            "emotional_turn": {"type": "string", "description": "情感转折"},
            "closing": {"type": "string", "description": "收尾"},
            "applicable_scenario": {"type": "string", "description": "这版脚本适合什么场景/什么风格的达人来讲"},
            "hotspot_reference": {
                "type": "string",
                "description": "如果用到了给定的热点参考，写出具体是哪一个；没有热点参考或者没用到就留空字符串",
            },
        },
        "required": ["scene_setup", "product_integration", "emotional_turn", "closing", "applicable_scenario"],
    },
}

_REVIEW_TOOL = {
    "name": _REVIEW_TOOL_NAME,
    "description": "写一版测评带货脚本",
    "input_schema": {
        "type": "object",
        "properties": {
            "unboxing": {"type": "string", "description": "开箱"},
            "trial_comparison": {"type": "string", "description": "现场试用/对比"},
            "verdict": {"type": "string", "description": "结论背书，强调真实感和可信度"},
            "applicable_scenario": {"type": "string", "description": "这版脚本适合什么场景/什么风格的达人来讲"},
            "hotspot_reference": {
                "type": "string",
                "description": "如果用到了给定的热点参考，写出具体是哪一个；没有热点参考或者没用到就留空字符串",
            },
        },
        "required": ["unboxing", "trial_comparison", "verdict", "applicable_scenario"],
    },
}

_HOTSPOT_INSTRUCTION = (
    "如果对话里给了热点参考，贴合的话可以自然融入（不要生硬硬套），"
    "用到了就在 hotspot_reference 里写清楚具体用了哪一条，没给热点参考或者没用上就留空字符串。"
)

_VOICEOVER_SYSTEM_PROMPT = (
    "你是达人运营的脚本创作助手，负责写口播带货脚本：痛点引入 → 卖点罗列 → 促单话术，"
    "节奏要快，依赖开头钩子抓住前 3 秒。必须贴合给到的达人内容风格和粉丝画像来写，不要写成通用模板腔。"
    f"{_HOTSPOT_INSTRUCTION}必须调用工具返回结构化结果，不要输出多余文字。"
)

_NARRATIVE_SYSTEM_PROMPT = (
    "你是达人运营的脚本创作助手，负责写剧情带货脚本：场景化短剧结构，商品作为解决方案自然植入，"
    "不要写成硬广。必须贴合给到的达人内容风格和粉丝画像来写。"
    f"{_HOTSPOT_INSTRUCTION}必须调用工具返回结构化结果，不要输出多余文字。"
)

_REVIEW_SYSTEM_PROMPT = (
    "你是达人运营的脚本创作助手，负责写测评带货脚本：开箱 → 现场试用/对比 → 结论背书，"
    "强调真实感和可信度。必须贴合给到的达人内容风格和粉丝画像来写。"
    f"{_HOTSPOT_INSTRUCTION}必须调用工具返回结构化结果，不要输出多余文字。"
)


def _build_brief(
    product: ProductProfile,
    influencer: InfluencerProfile,
    target_seconds: int,
    hotspot_context: str | None,
) -> str:
    lines = [
        f"商品：{product.name}",
        f"商品目标人群：{product.target_audience}",
        f"商品调性：{product.tone}",
        f"达人内容风格：{influencer.content_style}",
        f"达人粉丝画像：{influencer.audience_profile}",
        f"目标时长：约 {target_seconds} 秒",
    ]
    if hotspot_context:
        lines.append(f"当前热点参考：{hotspot_context}")
    return "\n".join(lines)


def _coerce_string_list(value: object) -> list[str]:
    # DeepSeek 的结构化输出偶尔不严格遵守数组类型，把 selling_points 整个吐成一个字符串——
    # 直接丢给模板会被 Jinja2 逐字符遍历，这里做一层防御：能当 JSON 数组解析就解析，不行就整体当一条卖点
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return parsed if isinstance(parsed, list) else [value]
    return [str(value)]


def _generate_sections(
    system_prompt: str,
    tool: dict,
    tool_name: str,
    product: ProductProfile,
    influencer: InfluencerProfile,
    target_seconds: int,
    hotspot_context: str | None,
) -> dict:
    brief = _build_brief(product, influencer, target_seconds, hotspot_context)
    response = create_message(
        system=system_prompt,
        messages=[{"role": "user", "content": brief}],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        max_tokens=2048,
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return tool_use.input


def generate_voiceover_sections(
    product: ProductProfile,
    influencer: InfluencerProfile,
    target_seconds: int = 30,
    hotspot_context: str | None = None,
) -> dict:
    sections = _generate_sections(
        _VOICEOVER_SYSTEM_PROMPT,
        _VOICEOVER_TOOL,
        _VOICEOVER_TOOL_NAME,
        product,
        influencer,
        target_seconds,
        hotspot_context,
    )
    sections["selling_points"] = _coerce_string_list(sections["selling_points"])
    return sections


def generate_narrative_sections(
    product: ProductProfile,
    influencer: InfluencerProfile,
    target_seconds: int = 30,
    hotspot_context: str | None = None,
) -> dict:
    return _generate_sections(
        _NARRATIVE_SYSTEM_PROMPT,
        _NARRATIVE_TOOL,
        _NARRATIVE_TOOL_NAME,
        product,
        influencer,
        target_seconds,
        hotspot_context,
    )


def generate_review_sections(
    product: ProductProfile,
    influencer: InfluencerProfile,
    target_seconds: int = 30,
    hotspot_context: str | None = None,
) -> dict:
    return _generate_sections(
        _REVIEW_SYSTEM_PROMPT,
        _REVIEW_TOOL,
        _REVIEW_TOOL_NAME,
        product,
        influencer,
        target_seconds,
        hotspot_context,
    )
