from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from integrations.llm_client import create_message

from .formulas import calculate_breakeven_commission_rate, calculate_gross_profit, calculate_profit
from .models import CostStructure, ProfitResult


class QueryIntent(str, Enum):
    NET_PROFIT = "net_profit"
    BREAKEVEN = "breakeven"


@dataclass(frozen=True)
class ExtractedQueryParams:
    intent: QueryIntent
    selling_price: Decimal
    influencer_commission_rate: Decimal | None  # BREAKEVEN 查询没有这个输入，为 None


_EXTRACT_TOOL_NAME = "record_profit_query_params"

_EXTRACT_TOOL = {
    "name": _EXTRACT_TOOL_NAME,
    "description": "从运营的自然语言提问中提取损益计算所需的结构化参数",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [intent.value for intent in QueryIntent],
                "description": (
                    "net_profit：已知售价和达人佣金率，问净利润/ROI/佣金空间；"
                    "breakeven：只问佣金给到多少还能保本，不涉及具体佣金率"
                ),
            },
            "selling_price": {"type": "number", "description": "商品售价，单位元"},
            "influencer_commission_rate": {
                "type": ["number", "null"],
                "description": "达人佣金率，换算成 0~1 之间的小数（如 30% 换算成 0.3）；intent 为 breakeven 时传 null",
            },
        },
        "required": ["intent", "selling_price", "influencer_commission_rate"],
    },
}

_EXTRACT_SYSTEM_PROMPT = (
    "你是达人运营损益计算助手的参数提取模块。"
    "只负责把运营的自然语言提问转成结构化参数，绝不自己计算或估算任何金额、比率。"
    "必须调用 record_profit_query_params 工具返回结果。"
)

_EXPLAIN_SYSTEM_PROMPT = (
    "你是达人运营损益计算助手的结果播报模块。"
    "下面会给你一组已经算好、精确到分的数字，把它们组织成一两句通顺自然的中文说明，语气像同事口头汇报。"
    "禁止修改、四舍五入或重新计算任何数字，必须原样使用给到你的数值。"
)


def extract_query_params(query: str) -> ExtractedQueryParams:
    response = create_message(
        system=_EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": query}],
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": _EXTRACT_TOOL_NAME},
        max_tokens=256,
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    raw = tool_use.input

    intent = QueryIntent(raw["intent"])
    rate = raw["influencer_commission_rate"]
    if intent is QueryIntent.NET_PROFIT and rate is None:
        raise ValueError("net_profit 查询必须提取出达人佣金率，LLM 返回了空值")

    return ExtractedQueryParams(
        intent=intent,
        selling_price=Decimal(str(raw["selling_price"])),
        influencer_commission_rate=Decimal(str(rate)) if rate is not None else None,
    )


def _explain(query: str, facts: str) -> str:
    response = create_message(
        system=_EXPLAIN_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"运营的提问：{query}\n\n已经算好的数字：\n{facts}\n\n请总结给运营看。",
            }
        ],
        max_tokens=256,
    )
    return "".join(block.text for block in response.content if block.type == "text")


def answer_net_profit_query(
    query: str,
    params: ExtractedQueryParams,
    cost_structure: CostStructure,
    platform_commission_rate: Decimal,
) -> tuple[ProfitResult, str]:
    if params.intent is not QueryIntent.NET_PROFIT or params.influencer_commission_rate is None:
        raise ValueError("answer_net_profit_query 只接受 intent=net_profit 且已提取佣金率的参数")

    result = calculate_profit(
        params.selling_price,
        cost_structure,
        platform_commission_rate,
        params.influencer_commission_rate,
    )
    commission_headroom = result.breakeven_commission_rate - params.influencer_commission_rate
    facts = (
        f"净利润：{result.net_profit:.2f} 元\n"
        f"ROI：{result.roi:.2f}\n"
        f"距离保本线还有 {commission_headroom:.2%} 的佣金空间"
    )
    explanation = _explain(query, facts)
    return result, explanation


def answer_breakeven_query(
    query: str,
    params: ExtractedQueryParams,
    cost_structure: CostStructure,
    platform_commission_rate: Decimal,
) -> tuple[Decimal, str]:
    if params.intent is not QueryIntent.BREAKEVEN:
        raise ValueError("answer_breakeven_query 只接受 intent=breakeven 的参数")

    gross_profit = calculate_gross_profit(params.selling_price, cost_structure, platform_commission_rate)
    breakeven_rate = calculate_breakeven_commission_rate(gross_profit, params.selling_price)
    facts = f"保本达人佣金率：{breakeven_rate:.2%}"
    explanation = _explain(query, facts)
    return breakeven_rate, explanation
