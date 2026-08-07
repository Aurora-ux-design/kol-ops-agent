from types import SimpleNamespace
from unittest.mock import patch

from engines.script.hotspot_notes import extract_hotspot_from_note


def _tool_use_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=payload)])


def test_extract_hotspot_from_note_returns_keyword_and_description() -> None:
    payload = {"keyword": "反问句钩子", "description": "开头用夸张反问句抓注意力，适合口播开场"}
    with patch(
        "engines.script.hotspot_notes.create_message", return_value=_tool_use_response(payload)
    ) as mock_call:
        keyword, description = extract_hotspot_from_note(
            "刷到好几个美妆达人开头都用很夸张的反问句，效果好像不错"
        )

    assert keyword == "反问句钩子"
    assert description == "开头用夸张反问句抓注意力，适合口播开场"
    prompt_content = mock_call.call_args.kwargs["messages"][0]["content"]
    assert "反问句" in prompt_content
