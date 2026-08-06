from __future__ import annotations

from contextlib import closing

from data import db as data_db
from engines.matching.coarse import influencer_row_to_profile
from engines.matching.pipeline import product_row_to_profile

from .compliance import check_compliance, load_banned_words
from .generate import generate_narrative_sections, generate_review_sections, generate_voiceover_sections
from .hotspots import format_hotspot_context, retrieve_relevant_hotspots
from .models import ScriptFormat, ScriptGenerationResult, ScriptVariant
from .templates import render_script

_GENERATORS = {
    ScriptFormat.VOICEOVER: generate_voiceover_sections,
    ScriptFormat.NARRATIVE: generate_narrative_sections,
    ScriptFormat.REVIEW: generate_review_sections,
}


def generate_scripts(
    product_id: str,
    influencer_id: str,
    target_seconds: int = 30,
    formats: list[ScriptFormat] | None = None,
) -> ScriptGenerationResult:
    formats = formats or list(ScriptFormat)
    banned_words = load_banned_words()

    with closing(data_db.get_connection()) as conn:
        product = product_row_to_profile(data_db.get_product(conn, product_id))
        influencer = influencer_row_to_profile(data_db.get_influencer(conn, influencer_id))

    relevant_hotspots = retrieve_relevant_hotspots(product, influencer)
    hotspot_context = format_hotspot_context(relevant_hotspots)

    variants = []
    for fmt in formats:
        raw_sections = _GENERATORS[fmt](product, influencer, target_seconds, hotspot_context)
        applicable_scenario = raw_sections.pop("applicable_scenario")
        hotspot_reference = raw_sections.pop("hotspot_reference", None) or None
        rendered_text = render_script(fmt, raw_sections)
        compliance_flags = check_compliance(rendered_text, banned_words)
        variants.append(
            ScriptVariant(
                format=fmt,
                sections=raw_sections,
                rendered_text=rendered_text,
                applicable_scenario=applicable_scenario,
                compliance_flags=compliance_flags,
                hotspot_reference=hotspot_reference,
            )
        )

    return ScriptGenerationResult(
        product_id=product_id, influencer_id=influencer_id, variants=tuple(variants)
    )
