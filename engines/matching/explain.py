from __future__ import annotations

from integrations.llm_client import create_message

from .models import MatchCandidate, ProductProfile

_EXPLAIN_TOOL_NAME = "record_match_reasons"

_EXPLAIN_TOOL = {
    "name": _EXPLAIN_TOOL_NAME,
    "description": "为每个达人候选写一句可读的匹配理由",
    "input_schema": {
        "type": "object",
        "properties": {
            "reasons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "influencer_id": {"type": "string"},
                        "reason": {
                            "type": "string",
                            "description": "一到两句话，引用给到的具体分数或事实，不要编造或修改数字",
                        },
                    },
                    "required": ["influencer_id", "reason"],
                },
            }
        },
        "required": ["reasons"],
    },
}

_EXPLAIN_SYSTEM_PROMPT = (
    "你是达人匹配助手的理由播报模块。"
    "下面会给你每个候选达人已经算好、精确到一位小数的 5 维度分数和依据，"
    "把它们组织成一到两句自然的中文理由。"
    "禁止修改、编造或重新计算任何数字，必须原样引用给到你的数值和事实。"
    "必须调用 record_match_reasons 工具返回结果。"
)


def _format_candidate_facts(candidate: MatchCandidate) -> str:
    lines = [f"达人 {candidate.influencer_id}（总分 {candidate.weighted_total:.1f}）："]
    for dim in candidate.dimension_scores:
        lines.append(f"- {dim.name}：{dim.score:.1f} 分（{dim.detail}）")
    return "\n".join(lines)


def explain_matches(product: ProductProfile, candidates: list[MatchCandidate]) -> dict[str, str]:
    facts_block = "\n\n".join(_format_candidate_facts(c) for c in candidates)
    response = create_message(
        system=_EXPLAIN_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"商品：{product.name}\n\n候选达人打分结果：\n{facts_block}",
            }
        ],
        tools=[_EXPLAIN_TOOL],
        tool_choice={"type": "tool", "name": _EXPLAIN_TOOL_NAME},
        max_tokens=1024,
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return {item["influencer_id"]: item["reason"] for item in tool_use.input["reasons"]}
