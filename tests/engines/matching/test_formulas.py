from datetime import date
from decimal import Decimal

from engines.matching.formulas import (
    calculate_weighted_total,
    cosine_similarity,
    min_max_normalize,
    rank_candidates,
    score_commission_fit,
    score_historical_performance,
    score_schedule_availability,
    semantic_similarity_to_score,
)
from engines.matching.models import DimensionScore, MatchCandidate

SUBWEIGHTS = {
    "gmv": Decimal("1") / Decimal("3"),
    "roi": Decimal("1") / Decimal("3"),
    "completion_rate": Decimal("1") / Decimal("3"),
}


def test_min_max_normalize_spreads_values_between_zero_and_one() -> None:
    result = min_max_normalize([Decimal("5000"), Decimal("8000"), Decimal("20000")])
    assert result == [Decimal("0"), Decimal("0.2"), Decimal("1")]


def test_min_max_normalize_all_equal_returns_neutral_score() -> None:
    result = min_max_normalize([Decimal("100"), Decimal("100"), Decimal("100")])
    assert result == [Decimal("0.5"), Decimal("0.5"), Decimal("0.5")]


def test_min_max_normalize_empty_list() -> None:
    assert min_max_normalize([]) == []


def test_score_historical_performance_averages_three_normalized_metrics() -> None:
    score = score_historical_performance(
        gmv_norm=Decimal("1"), roi_norm=Decimal("0.5"), completion_norm=Decimal("0"), subweights=SUBWEIGHTS
    )
    # 1/3 在十进制下是无限循环小数，Decimal 只能截断到有限位，
    # 三份相加会有一点点舍入残差（约 1e-27），量化到合理精度后再比较
    assert score.quantize(Decimal("0.0001")) == Decimal("50.0000")


class TestCommissionFitBoundary:
    def test_full_range_within_budget_scores_100(self) -> None:
        # 达人区间 [20%,35%]，商品保本线 45%，整个区间都在预算内
        score = score_commission_fit(Decimal("0.20"), Decimal("0.35"), Decimal("0.45"))
        assert score == Decimal("100")

    def test_range_entirely_above_breakeven_scores_0(self) -> None:
        # 达人最低都比保本线高，完全不匹配
        score = score_commission_fit(Decimal("0.50"), Decimal("0.60"), Decimal("0.45"))
        assert score == Decimal("0")

    def test_partial_overlap(self) -> None:
        # 达人区间 [20%,50%]，保本线 45%，重合 [20%,45%]，占达人区间 30/30=... 实际宽度25
        score = score_commission_fit(Decimal("0.20"), Decimal("0.50"), Decimal("0.45"))
        assert score == Decimal("100") * Decimal("0.25") / Decimal("0.30")

    def test_zero_width_range_at_or_below_breakeven_scores_100(self) -> None:
        score = score_commission_fit(Decimal("0.30"), Decimal("0.30"), Decimal("0.45"))
        assert score == Decimal("100")

    def test_zero_width_range_above_breakeven_scores_0(self) -> None:
        score = score_commission_fit(Decimal("0.50"), Decimal("0.50"), Decimal("0.45"))
        assert score == Decimal("0")


class TestScheduleAvailabilityBoundary:
    def test_available_today_scores_100(self) -> None:
        score = score_schedule_availability(
            date(2026, 8, 3), date(2026, 8, 3), max_wait_days=30
        )
        assert score == Decimal("100")

    def test_available_before_requested_date_scores_100(self) -> None:
        score = score_schedule_availability(
            date(2026, 7, 20), date(2026, 8, 3), max_wait_days=30
        )
        assert score == Decimal("100")

    def test_halfway_to_max_wait_days_scores_50(self) -> None:
        score = score_schedule_availability(
            date(2026, 8, 18), date(2026, 8, 3), max_wait_days=30
        )
        assert score == Decimal("50")

    def test_exactly_at_max_wait_days_scores_0(self) -> None:
        score = score_schedule_availability(
            date(2026, 9, 2), date(2026, 8, 3), max_wait_days=30
        )
        assert score == Decimal("0")

    def test_beyond_max_wait_days_clamped_to_0(self) -> None:
        score = score_schedule_availability(
            date(2026, 12, 1), date(2026, 8, 3), max_wait_days=30
        )
        assert score == Decimal("0")


def test_cosine_similarity_identical_vectors_is_one() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors_is_zero() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_zero_vector_is_safe() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_semantic_similarity_to_score_clamps_negative_to_zero() -> None:
    assert semantic_similarity_to_score(-0.3) == Decimal("0")


def test_semantic_similarity_to_score_clamps_above_one_to_100() -> None:
    assert semantic_similarity_to_score(1.2) == Decimal("100")


def test_semantic_similarity_to_score_normal_mapping() -> None:
    assert semantic_similarity_to_score(0.82) == Decimal("82.0")


def test_calculate_weighted_total() -> None:
    dimension_scores = {
        "audience_overlap": Decimal("80"),
        "historical_performance": Decimal("60"),
        "content_style_match": Decimal("70"),
        "commission_fit": Decimal("100"),
        "schedule_availability": Decimal("50"),
    }
    weights = {
        "audience_overlap": Decimal("0.25"),
        "historical_performance": Decimal("0.25"),
        "content_style_match": Decimal("0.20"),
        "commission_fit": Decimal("0.15"),
        "schedule_availability": Decimal("0.15"),
    }
    total = calculate_weighted_total(dimension_scores, weights)
    assert total == Decimal("80") * Decimal("0.25") + Decimal("60") * Decimal("0.25") + Decimal(
        "70"
    ) * Decimal("0.20") + Decimal("100") * Decimal("0.15") + Decimal("50") * Decimal("0.15")


def _candidate(influencer_id: str, weighted_total: Decimal) -> MatchCandidate:
    return MatchCandidate(
        influencer_id=influencer_id,
        dimension_scores=(DimensionScore(name="audience_overlap", score=Decimal("80"), detail=""),),
        weighted_total=weighted_total,
    )


def test_rank_candidates_sorts_by_weighted_total_descending() -> None:
    candidates = [_candidate("INF001", Decimal("70")), _candidate("INF002", Decimal("90"))]
    ranked = rank_candidates(candidates, top_n=5)
    assert [c.influencer_id for c in ranked] == ["INF002", "INF001"]


def test_rank_candidates_ties_broken_by_influencer_id() -> None:
    candidates = [_candidate("INF002", Decimal("80")), _candidate("INF001", Decimal("80"))]
    ranked = rank_candidates(candidates, top_n=5)
    assert [c.influencer_id for c in ranked] == ["INF001", "INF002"]


def test_rank_candidates_truncates_to_top_n() -> None:
    candidates = [
        _candidate("INF001", Decimal("70")),
        _candidate("INF002", Decimal("90")),
        _candidate("INF003", Decimal("80")),
    ]
    ranked = rank_candidates(candidates, top_n=2)
    assert [c.influencer_id for c in ranked] == ["INF002", "INF003"]
