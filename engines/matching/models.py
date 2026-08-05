from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from engines.profit import CostStructure


@dataclass(frozen=True)
class InfluencerProfile:
    influencer_id: str
    name: str
    category_tags: str
    audience_profile: str
    content_style: str
    follower_count: int
    historical_gmv_avg: Decimal
    historical_roi_avg: Decimal
    historical_completion_rate: Decimal
    commission_rate_min: Decimal
    commission_rate_max: Decimal
    schedule_available_from: date


@dataclass(frozen=True)
class ProductProfile:
    product_id: str
    name: str
    category: str
    target_audience: str
    tone: str
    selling_price: Decimal
    cost_structure: CostStructure
    platform_commission_rate: Decimal


@dataclass(frozen=True)
class DimensionScore:
    name: str
    score: Decimal  # 0-100
    detail: str  # 这一维度打分依据的人类可读事实，供 LLM 生成理由时引用，不是理由本身


@dataclass(frozen=True)
class MatchCandidate:
    influencer_id: str
    dimension_scores: tuple[DimensionScore, ...]
    weighted_total: Decimal
    reason: str | None = None  # 只有进入 Top N 的候选才会回填


@dataclass(frozen=True)
class MatchResult:
    product_id: str
    requested_date: date
    candidates: tuple[MatchCandidate, ...]  # 已按 weighted_total 排序，长度即 top_n
