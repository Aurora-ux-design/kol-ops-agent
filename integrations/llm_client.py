from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Union

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=DEFAULT_BASE_URL,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    return _client


# 下面这三个类模拟 Anthropic Message 的 .content 形状（block.type + .input / .text），
# 这样 nl_query.py / explain.py 里解析 response.content 的代码不用因为换供应商而改。
@dataclass
class ToolUseBlock:
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class TextBlock:
    text: str
    type: str = "text"


ContentBlock = Union[ToolUseBlock, TextBlock]


@dataclass
class Message:
    content: list[ContentBlock]
    stop_reason: str | None


def _to_openai_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    if tools is None:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tools
    ]


def _to_openai_tool_choice(tool_choice: dict[str, Any] | None) -> dict[str, Any] | None:
    if tool_choice is None:
        return None
    return {"type": "function", "function": {"name": tool_choice["name"]}}


def create_message(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
) -> Message:
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, *messages],
    }
    openai_tools = _to_openai_tools(tools)
    if openai_tools is not None:
        kwargs["tools"] = openai_tools
    openai_tool_choice = _to_openai_tool_choice(tool_choice)
    if openai_tool_choice is not None:
        kwargs["tool_choice"] = openai_tool_choice

    logger.info("llm request model=%s", model)
    response = get_client().chat.completions.create(**kwargs)
    choice = response.choices[0]
    logger.info("llm response finish_reason=%s", choice.finish_reason)

    content: list[ContentBlock] = []
    if choice.message.tool_calls:
        for tool_call in choice.message.tool_calls:
            raw_arguments = tool_call.function.arguments
            try:
                parsed_arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                # DeepSeek 偶尔会返回没转义好的 tool call 参数（比如字符串里混进未转义的换行），
                # 把 finish_reason 和原始内容带出来，比只看 json 报的字符位置好排查得多
                raise ValueError(
                    f"DeepSeek 返回的 tool call 参数不是合法 JSON"
                    f"（finish_reason={choice.finish_reason}）：\n{raw_arguments}"
                ) from exc
            content.append(ToolUseBlock(input=parsed_arguments))
    if choice.message.content:
        content.append(TextBlock(text=choice.message.content))

    return Message(content=content, stop_reason=choice.finish_reason)
