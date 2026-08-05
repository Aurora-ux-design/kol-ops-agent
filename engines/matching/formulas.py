from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from .models import MatchCandidate


def min_max_normalize(values: list[Decimal]) -> list[Decimal]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        # 候选池里这项指标完全一样，没有区分度信息，给中性分而不是除零
        return [Decimal("0.5") for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def score_historical_performance(
    gmv_norm: Decimal,
    roi_norm: Decimal,
    completion_norm: Decimal,
    subweights: dict[str, Decimal],
) -> Decimal:
    weighted = (
        gmv_norm * subweights["gmv"]
        + roi_norm * subweights["roi"]
        + completion_norm * subweights["completion_rate"]
    )
    return weighted * Decimal("100")


def score_commission_fit(
    commission_min: Decimal, commission_max: Decimal, breakeven_rate: Decimal
) -> Decimal:
    range_width = commission_max - commission_min
    if range_width == 0:
        return Decimal("100") if commission_min <= breakeven_rate else Decimal("0")
    overlap = max(Decimal("0"), min(commission_max, breakeven_rate) - commission_min)
    return Decimal("100") * overlap / range_width


def score_schedule_availability(
    available_from: date, requested_date: date, max_wait_days: int
) -> Decimal:
    wait_days = max(0, (available_from - requested_date).days)
    if wait_days == 0:
        return Decimal("100")
    ratio = Decimal(1) - Decimal(wait_days) / Decimal(max_wait_days)
    return Decimal("100") * max(Decimal("0"), ratio)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_similarity_to_score(cosine_sim: float) -> Decimal:
    clamped = max(0.0, min(1.0, cosine_sim))
    return Decimal(str(clamped)) * Decimal("100")


def calculate_weighted_total(
    dimension_scores: dict[str, Decimal], weights: dict[str, Decimal]
) -> Decimal:
    return sum(
        (dimension_scores[name] * weight for name, weight in weights.items()),
        start=Decimal("0"),
    )


def rank_candidates(candidates: list[MatchCandidate], top_n: int) -> list[MatchCandidate]:
    ranked = sorted(candidates, key=lambda c: (-c.weighted_total, c.influencer_id))
    return ranked[:top_n]
