from decimal import Decimal

import pytest

from engines.profit import CostStructure, calculate_profit
from engines.profit.formulas import (
    calculate_breakeven_commission_rate,
    calculate_gross_profit,
    calculate_influencer_commission,
    calculate_net_profit,
    calculate_platform_commission,
    calculate_roi,
)

SELLING_PRICE = Decimal("200")
PLATFORM_COMMISSION_RATE = Decimal("0.05")


@pytest.fixture
def cost_structure() -> CostStructure:
    return CostStructure(
        purchase_cost=Decimal("80"),
        packaging_fee=Decimal("5"),
        logistics_fee=Decimal("8"),
        overhead_fee=Decimal("2"),
        platform_tech_fee=Decimal("3"),
        tax=Decimal("2"),
    )


def test_cost_structure_total(cost_structure: CostStructure) -> None:
    assert cost_structure.total == Decimal("100")


def test_calculate_platform_commission() -> None:
    assert calculate_platform_commission(SELLING_PRICE, PLATFORM_COMMISSION_RATE) == Decimal("10")


def test_calculate_gross_profit(cost_structure: CostStructure) -> None:
    gross_profit = calculate_gross_profit(SELLING_PRICE, cost_structure, PLATFORM_COMMISSION_RATE)
    assert gross_profit == Decimal("90")


def test_calculate_influencer_commission() -> None:
    assert calculate_influencer_commission(SELLING_PRICE, Decimal("0.3")) == Decimal("60")


def test_calculate_net_profit() -> None:
    assert calculate_net_profit(Decimal("90"), Decimal("60")) == Decimal("30")


def test_calculate_roi() -> None:
    roi = calculate_roi(SELLING_PRICE, Decimal("100"), Decimal("10"), Decimal("60"))
    assert roi == Decimal("200") / Decimal("170")


def test_calculate_breakeven_commission_rate() -> None:
    assert calculate_breakeven_commission_rate(Decimal("90"), SELLING_PRICE) == Decimal("0.45")


def test_calculate_profit_end_to_end(cost_structure: CostStructure) -> None:
    result = calculate_profit(SELLING_PRICE, cost_structure, PLATFORM_COMMISSION_RATE, Decimal("0.3"))

    assert result.total_cost == Decimal("100")
    assert result.platform_commission == Decimal("10")
    assert result.gross_profit == Decimal("90")
    assert result.influencer_commission == Decimal("60")
    assert result.net_profit == Decimal("30")
    assert result.roi == Decimal("200") / Decimal("170")
    assert result.breakeven_commission_rate == Decimal("0.45")


class TestBreakevenBoundary:
    # 保本佣金率 = 毛利 / 售价 = 90 / 200 = 0.45（PRD 6.2 的临界点定义）

    def test_commission_rate_exactly_at_breakeven_yields_zero_net_profit(
        self, cost_structure: CostStructure
    ) -> None:
        result = calculate_profit(SELLING_PRICE, cost_structure, PLATFORM_COMMISSION_RATE, Decimal("0.45"))

        assert result.breakeven_commission_rate == Decimal("0.45")
        assert result.net_profit == Decimal("0")

    def test_commission_rate_just_below_breakeven_is_profitable(
        self, cost_structure: CostStructure
    ) -> None:
        result = calculate_profit(
            SELLING_PRICE, cost_structure, PLATFORM_COMMISSION_RATE, Decimal("0.4499")
        )

        assert result.net_profit > Decimal("0")

    def test_commission_rate_just_above_breakeven_is_a_loss(
        self, cost_structure: CostStructure
    ) -> None:
        result = calculate_profit(
            SELLING_PRICE, cost_structure, PLATFORM_COMMISSION_RATE, Decimal("0.4501")
        )

        assert result.net_profit < Decimal("0")

    def test_zero_commission_rate_equals_gross_profit(self, cost_structure: CostStructure) -> None:
        result = calculate_profit(SELLING_PRICE, cost_structure, PLATFORM_COMMISSION_RATE, Decimal("0"))

        assert result.influencer_commission == Decimal("0")
        assert result.net_profit == result.gross_profit


def test_zero_cost_structure_has_zero_total() -> None:
    zero_cost = CostStructure(
        purchase_cost=Decimal("0"),
        packaging_fee=Decimal("0"),
        logistics_fee=Decimal("0"),
        overhead_fee=Decimal("0"),
        platform_tech_fee=Decimal("0"),
        tax=Decimal("0"),
    )
    assert zero_cost.total == Decimal("0")


def test_roi_raises_when_denominator_is_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        calculate_roi(SELLING_PRICE, Decimal("0"), Decimal("0"), Decimal("0"))
