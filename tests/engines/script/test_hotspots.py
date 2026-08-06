from engines.script.hotspots import format_hotspot_context
from engines.script.models import HotspotEntry


def _hotspot(keyword: str, description: str) -> HotspotEntry:
    return HotspotEntry(
        hotspot_id="1",
        keyword=keyword,
        description=description,
        is_enabled=True,
        created_at="2026-08-05T00:00:00",
    )


def test_format_hotspot_context_empty_list_returns_none() -> None:
    assert format_hotspot_context([]) is None


def test_format_hotspot_context_single_entry() -> None:
    result = format_hotspot_context([_hotspot("秋天的第一杯奶茶", "情感共鸣类 Hook")])
    assert result == "秋天的第一杯奶茶——情感共鸣类 Hook"


def test_format_hotspot_context_multiple_entries_joined() -> None:
    result = format_hotspot_context(
        [_hotspot("热点A", "描述A"), _hotspot("热点B", "描述B")]
    )
    assert result == "热点A——描述A；热点B——描述B"
