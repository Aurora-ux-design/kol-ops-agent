from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .models import ScriptFormat

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

_TEMPLATE_FILENAMES = {
    ScriptFormat.VOICEOVER: "voiceover/script.jinja2",
    ScriptFormat.NARRATIVE: "narrative/script.jinja2",
    ScriptFormat.REVIEW: "review/script.jinja2",
}

_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), trim_blocks=True, lstrip_blocks=True)


def render_script(format: ScriptFormat, sections: dict) -> str:
    template = _env.get_template(_TEMPLATE_FILENAMES[format])
    return template.render(**sections).strip()
