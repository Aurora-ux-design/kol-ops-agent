from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CostStructure:
    """商品成本结构，来自 ERP（PRD 6.2）。"""

    purchase_cost: Decimal
    packaging_fee: Decimal
    logistics_fee: Decimal
    overhead_fee: Decimal
    platform_tech_fee: Decimal
    tax: Decimal

    @property
    def total(self) -> Decimal:
        return (
            self.purchase_cost
            + self.packaging_fee
            + self.logistics_fee
            + self.overhead_fee
            + self.platform_tech_fee
            + self.tax
        )


@dataclass(frozen=True)
class ProfitResult:
    selling_price: Decimal
    total_cost: Decimal
    platform_commission: Decimal
    gross_profit: Decimal
    influencer_commission: Decimal
    net_profit: Decimal
    roi: Decimal
    breakeven_commission_rate: Decimal
