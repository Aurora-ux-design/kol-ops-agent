from __future__ import annotations

from decimal import Decimal

from .models import CostStructure, ProfitResult


def calculate_platform_commission(
    selling_price: Decimal, platform_commission_rate: Decimal
) -> Decimal:
    return selling_price * platform_commission_rate


def calculate_gross_profit(
    selling_price: Decimal,
    cost_structure: CostStructure,
    platform_commission_rate: Decimal,
) -> Decimal:
    platform_commission = calculate_platform_commission(selling_price, platform_commission_rate)
    return selling_price - cost_structure.total - platform_commission


def calculate_influencer_commission(
    selling_price: Decimal, influencer_commission_rate: Decimal
) -> Decimal:
    return selling_price * influencer_commission_rate


def calculate_net_profit(gross_profit: Decimal, influencer_commission: Decimal) -> Decimal:
    return gross_profit - influencer_commission


def calculate_roi(
    selling_price: Decimal,
    total_cost: Decimal,
    platform_commission: Decimal,
    influencer_commission: Decimal,
) -> Decimal:
    return selling_price / (total_cost + platform_commission + influencer_commission)


def calculate_breakeven_commission_rate(gross_profit: Decimal, selling_price: Decimal) -> Decimal:
    return gross_profit / selling_price


def calculate_profit(
    selling_price: Decimal,
    cost_structure: CostStructure,
    platform_commission_rate: Decimal,
    influencer_commission_rate: Decimal,
) -> ProfitResult:
    total_cost = cost_structure.total
    platform_commission = calculate_platform_commission(selling_price, platform_commission_rate)
    gross_profit = calculate_gross_profit(selling_price, cost_structure, platform_commission_rate)
    influencer_commission = calculate_influencer_commission(selling_price, influencer_commission_rate)
    net_profit = calculate_net_profit(gross_profit, influencer_commission)
    roi = calculate_roi(selling_price, total_cost, platform_commission, influencer_commission)
    breakeven_commission_rate = calculate_breakeven_commission_rate(gross_profit, selling_price)

    return ProfitResult(
        selling_price=selling_price,
        total_cost=total_cost,
        platform_commission=platform_commission,
        gross_profit=gross_profit,
        influencer_commission=influencer_commission,
        net_profit=net_profit,
        roi=roi,
        breakeven_commission_rate=breakeven_commission_rate,
    )
