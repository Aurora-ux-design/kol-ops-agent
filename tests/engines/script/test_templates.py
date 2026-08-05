from engines.script.models import ScriptFormat
from engines.script.templates import render_script


def test_render_voiceover_script_includes_all_sections() -> None:
    text = render_script(
        ScriptFormat.VOICEOVER,
        {
            "hook": "开头钩子文案",
            "pain_point": "痛点描述",
            "selling_points": ["卖点一", "卖点二"],
            "call_to_action": "现在下单",
        },
    )
    assert "开头钩子文案" in text
    assert "痛点描述" in text
    assert "1. 卖点一" in text
    assert "2. 卖点二" in text
    assert "现在下单" in text
    assert "【开头钩子】" in text


def test_render_narrative_script_includes_all_sections() -> None:
    text = render_script(
        ScriptFormat.NARRATIVE,
        {
            "scene_setup": "场景铺垫文案",
            "product_integration": "商品植入文案",
            "emotional_turn": "情感转折文案",
            "closing": "收尾文案",
        },
    )
    assert "场景铺垫文案" in text
    assert "商品植入文案" in text
    assert "情感转折文案" in text
    assert "收尾文案" in text


def test_render_review_script_includes_all_sections() -> None:
    text = render_script(
        ScriptFormat.REVIEW,
        {
            "unboxing": "开箱文案",
            "trial_comparison": "试用对比文案",
            "verdict": "结论文案",
        },
    )
    assert "开箱文案" in text
    assert "试用对比文案" in text
    assert "结论文案" in text
