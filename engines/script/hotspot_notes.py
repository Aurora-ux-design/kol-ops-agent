from __future__ import annotations

from integrations.llm_client import create_message

_EXTRACT_TOOL_NAME = "record_hotspot_from_note"

_EXTRACT_TOOL = {
    "name": _EXTRACT_TOOL_NAME,
    "description": "把运营的自由文字备注提炼成热点库需要的关键词标签和结构化描述",
    "input_schema": {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "一个简短的关键词/标签，概括这条热点，几个字到十几个字",
            },
            "description": {
                "type": "string",
                "description": "结构化描述这个热点的具体表现、适用场景，基于备注原文整理，不要编造备注里没有的信息",
            },
        },
        "required": ["keyword", "description"],
    },
}

_EXTRACT_SYSTEM_PROMPT = (
    "你是达人运营脚本创作助手的热点录入模块。"
    "运营会给你一段自由文字备注，记录他们观察到的热点/梗/内容套路。"
    "你只负责把这段备注提炼成一个简短关键词标签和一段结构化描述，不要编造备注里没提到的内容。"
    "必须调用工具返回结构化结果，不要输出多余文字。"
)


def extract_hotspot_from_note(note: str) -> tuple[str, str]:
    response = create_message(
        system=_EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": note}],
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": _EXTRACT_TOOL_NAME},
        max_tokens=512,
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return tool_use.input["keyword"], tool_use.input["description"]
