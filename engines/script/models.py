from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScriptFormat(str, Enum):
    VOICEOVER = "voiceover"
    NARRATIVE = "narrative"
    REVIEW = "review"


@dataclass(frozen=True)
class ScriptVariant:
    format: ScriptFormat
    sections: dict[str, str | list[str]]
    rendered_text: str
    applicable_scenario: str
    compliance_flags: tuple[str, ...]
    hotspot_reference: str | None = None


@dataclass(frozen=True)
class ScriptGenerationResult:
    product_id: str
    influencer_id: str
    variants: tuple[ScriptVariant, ...]


@dataclass(frozen=True)
class HotspotEntry:
    hotspot_id: str
    keyword: str
    description: str
    is_enabled: bool
    created_at: str
