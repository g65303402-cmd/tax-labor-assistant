"""2026년 노무·급여 계산 기준값.

모든 값은 연도별로 바뀌므로 한 곳에서만 관리한다.
출처를 주석으로 남기고, 매년 1월/7월 공단 고시를 확인해 갱신할 것.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Rates:
    year: int

    # 최저임금 (고용노동부고시 제2025-47호): 2026년 시간급 10,320원
    minimum_hourly_wage: int

    # 국민연금: 2026년 총 9.5% (근로자·사업주 각 4.75%)
    pension_employee: float
    pension_employer: float

    # 건강보험: 2026년 총 7.19% (근로자·사업주 각 3.595%)
    health_employee: float
    health_employer: float

    # 장기요양보험: 소득 대비 0.9448% → 건강보험료 × (0.9448 / 7.19)
    long_term_care_income_rate: float
    health_total_rate: float

    # 고용보험(실업급여): 근로자 0.9%, 사업주 0.9%
    employment_employee: float
    employment_employer_unemployment: float

    # 국민연금 기준소득월액 상·하한 (매년 7월 변경).
    # TODO: 국민연금공단 고시값을 확인한 뒤 입력. None이면 상·하한을 적용하지 않는다.
    pension_base_min: Optional[int] = None
    pension_base_max: Optional[int] = None

    @property
    def long_term_care_ratio_of_health(self) -> float:
        """건강보험료 대비 장기요양보험료 비율 (2026년 약 13.14%)."""
        return self.long_term_care_income_rate / self.health_total_rate


RATES_2026 = Rates(
    year=2026,
    minimum_hourly_wage=10_320,
    pension_employee=0.0475,
    pension_employer=0.0475,
    health_employee=0.03595,
    health_employer=0.03595,
    long_term_care_income_rate=0.009448,
    health_total_rate=0.0719,
    employment_employee=0.009,
    employment_employer_unemployment=0.009,
)

# 고용보험 사업주 추가 부담분(고용안정·직업능력개발사업), 사업장 규모별
EMPLOYMENT_STABILITY_RATES = {
    "under_150": 0.0025,               # 150인 미만
    "150_plus_priority": 0.0045,       # 150인 이상 우선지원대상기업
    "150_to_999": 0.0065,              # 150인 이상 1,000인 미만
    "1000_plus_or_public": 0.0085,     # 1,000인 이상 / 국가·지자체
}

CURRENT = RATES_2026
