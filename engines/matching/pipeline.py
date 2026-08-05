from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path

from data import db as data_db
from data import vector_store
from engines.profit import CostStructure
from engines.profit.formulas import calculate_breakeven_commission_rate, calculate_gross_profit

from .coarse import coarse_rank_influencers
from .explain import explain_matches
from .formulas import (
    calculate_weighted_total,
    min_max_normalize,
    rank_candidates,
    score_commission_fit,
    score_historical_performance,
    score_schedule_availability,
    semantic_similarity_to_score,
)
from .models import DimensionScore, MatchCandidate, MatchResult, ProductProfile

_WEIGHTS_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "matching_weights.json"


def _load_weights_config() -> dict:
    with _WEIGHTS_CONFIG_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)
    return {
        "dimension_weights": {k: Decimal(str(v)) for k, v in raw["dimension_weights"].items()},
        "historical_performance_subweights": {
            k: Decimal(str(v)) for k, v in raw["historical_performance_subweights"].items()
        },
        "max_wait_days": int(raw["max_wait_days"]),
    }


def product_row_to_profile(row: sqlite3.Row) -> ProductProfile:
    return ProductProfile(
        product_id=row["product_id"],
        name=row["name"],
        category=row["category"],
        target_audience=row["target_audience"],
        tone=row["tone"],
        selling_price=Decimal(row["selling_price"]),
        cost_structure=CostStructure(
            purchase_cost=Decimal(row["purchase_cost"]),
            packaging_fee=Decimal(row["packaging_fee"]),
            logistics_fee=Decimal(row["logistics_fee"]),
            overhead_fee=Decimal(row["overhead_fee"]),
            platform_tech_fee=Decimal(row["platform_tech_fee"]),
            tax=Decimal(row["tax"]),
        ),
        platform_commission_rate=Decimal(row["platform_commission_rate"]),
    )


def load_product(conn: sqlite3.Connection, product_id: str) -> ProductProfile:
    return product_row_to_profile(data_db.get_product(conn, product_id))


def match_influencers(
    product_id: str,
    requested_date: date | None = None,
    top_n: int = 5,
    coarse_top_n: int = 30,
) -> MatchResult:
    requested_date = requested_date or date.today()
    weights = _load_weights_config()

    with closing(data_db.get_connection()) as conn:
        product = load_product(conn, product_id)

        chroma_client = vector_store.get_client()
        coarse_candidates = coarse_rank_influencers(conn, chroma_client, product, top_n=coarse_top_n)

        breakeven_rate = calculate_breakeven_commission_rate(
            calculate_gross_profit(
                product.selling_price, product.cost_structure, product.platform_commission_rate
            ),
            product.selling_price,
        )

        gmv_norms = min_max_normalize([i.historical_gmv_avg for i, _, _ in coarse_candidates])
        roi_norms = min_max_normalize([i.historical_roi_avg for i, _, _ in coarse_candidates])
        completion_norms = min_max_normalize(
            [i.historical_completion_rate for i, _, _ in coarse_candidates]
        )

        candidates: list[MatchCandidate] = []
        for (influencer, audience_sim, style_sim), gmv_norm, roi_norm, completion_norm in zip(
            coarse_candidates, gmv_norms, roi_norms, completion_norms
        ):
            audience_score = semantic_similarity_to_score(audience_sim)
            style_score = semantic_similarity_to_score(style_sim)
            historical_score = score_historical_performance(
                gmv_norm, roi_norm, completion_norm, weights["historical_performance_subweights"]
            )
            commission_score = score_commission_fit(
                influencer.commission_rate_min, influencer.commission_rate_max, breakeven_rate
            )
            schedule_score = score_schedule_availability(
                influencer.schedule_available_from, requested_date, weights["max_wait_days"]
            )

            dimension_scores = (
                DimensionScore(
                    name="audience_overlap",
                    score=audience_score,
                    detail=f"粉丝画像与商品目标人群向量相似度 {audience_sim:.2f}",
                ),
                DimensionScore(
                    name="historical_performance",
                    score=historical_score,
                    detail=(
                        f"历史GMV均值{influencer.historical_gmv_avg}元、"
                        f"ROI均值{influencer.historical_roi_avg}、"
                        f"完播率{influencer.historical_completion_rate:.0%}，候选池内相对表现"
                    ),
                ),
                DimensionScore(
                    name="content_style_match",
                    score=style_score,
                    detail=f"内容风格与商品调性向量相似度 {style_sim:.2f}",
                ),
                DimensionScore(
                    name="commission_fit",
                    score=commission_score,
                    detail=(
                        f"达人历史佣金率区间 {influencer.commission_rate_min:.0%}~"
                        f"{influencer.commission_rate_max:.0%}，商品保本佣金率 {breakeven_rate:.0%}"
                    ),
                ),
                DimensionScore(
                    name="schedule_availability",
                    score=schedule_score,
                    detail=f"达人下次可用日期 {influencer.schedule_available_from.isoformat()}",
                ),
            )
            dimension_score_map = {d.name: d.score for d in dimension_scores}
            weighted_total = calculate_weighted_total(dimension_score_map, weights["dimension_weights"])

            candidates.append(
                MatchCandidate(
                    influencer_id=influencer.influencer_id,
                    dimension_scores=dimension_scores,
                    weighted_total=weighted_total,
                )
            )

        top_candidates = rank_candidates(candidates, top_n=top_n)
        reasons = explain_matches(product, top_candidates)
        final_candidates = tuple(
            MatchCandidate(
                influencer_id=c.influencer_id,
                dimension_scores=c.dimension_scores,
                weighted_total=c.weighted_total,
                reason=reasons.get(c.influencer_id),
            )
            for c in top_candidates
        )

        result = MatchResult(
            product_id=product.product_id, requested_date=requested_date, candidates=final_candidates
        )

        data_db.record_match(
            conn,
            product_id=result.product_id,
            requested_date=result.requested_date.isoformat(),
            weights_snapshot=weights,
            candidates_snapshot=[
                {
                    "influencer_id": c.influencer_id,
                    "dimension_scores": [
                        {"name": d.name, "score": d.score, "detail": d.detail}
                        for d in c.dimension_scores
                    ],
                    "weighted_total": c.weighted_total,
                    "reason": c.reason,
                }
                for c in result.candidates
            ],
        )

        return result
