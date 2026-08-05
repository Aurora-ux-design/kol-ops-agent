from __future__ import annotations

import json
from pathlib import Path

_COMPLIANCE_WORDS_PATH = Path(__file__).parent.parent.parent / "config" / "compliance_words.json"


def load_banned_words(path: Path = _COMPLIANCE_WORDS_PATH) -> list[str]:
    with path.open(encoding="utf-8") as f:
        config = json.load(f)
    return config["banned_words"]


def check_compliance(text: str, banned_words: list[str]) -> tuple[str, ...]:
    lowered = text.lower()
    return tuple(word for word in banned_words if word.lower() in lowered)
