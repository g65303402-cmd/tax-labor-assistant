"""급여·노무 계산 도구.

LLM은 숫자 계산을 직접 하지 않는다. 계산은 전부 이 모듈의 함수가 담당하고,
LLM은 어떤 함수를 부를지 결정한 뒤 결과를 설명만 한다.

표준 라이브러리만 사용한다 (테스트를 가볍게 유지하기 위해).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import ROUND_FLOOR, Decimal

from app.tools.rates import CURRENT, EMPLOYMENT_STABILITY_RATES, Rates

WEEKS_PER_MONTH = 365 / 7 / 12  # 약 4.345주


def _premium(base: float, rate: float) -> int:
    """base × rate를 10원 미만 절사. 부동소수점 오차(예: 27000 → 26999.99)를 막기 위해 Decimal 사용."""
    amount = Decimal(str(base)) * Decimal(str(rate))
    return int((amount / 10).to_integral_value(rounding=ROUND_FLOOR) * 10)


# ---------------------------------------------------------------------------
# 주휴수당 (근로기준법 제55조, 시행령 제30조 / 제18조 제3항)
# ---------------------------------------------------------------------------
def weekly_holiday_hours(weekly_hours: float) -> float:
    """1주 소정근로시간에 비례한 주휴시간. 15시간 미만이면 0, 최대 8시간."""
    if weekly_hours < 15:
        return 0.0
    return min(weekly_hours, 40) / 40 * 8


@dataclass
class WeeklyHolidayPayResult:
    eligible: bool
    reason: str
    holiday_hours: float
    weekly_holiday_pay: int
    legal_basis: str = "근로기준법 제55조, 같은 법 시행령 제30조, 제18조 제3항"


def weekly_holiday_pay(
    hourly_wage: float, weekly_hours: float, attended_all_days: bool = True
) -> WeeklyHolidayPayResult:
    if weekly_hours < 15:
        return WeeklyHolidayPayResult(False, "1주 소정근로시간이 15시간 미만이면 주휴수당이 없습니다.", 0.0, 0)
    if not attended_all_days:
        return WeeklyHolidayPayResult(False, "그 주의 소정근로일을 개근하지 않으면 주휴수당이 발생하지 않습니다.", 0.0, 0)
    hours = weekly_holiday_hours(weekly_hours)
    return WeeklyHolidayPayResult(True, "주 15시간 이상, 개근 조건을 충족합니다.", round(hours, 2), int(round(hourly_wage * hours)))


# ---------------------------------------------------------------------------
# 최저임금 (최저임금법, 고용노동부고시 제2025-47호)
# ---------------------------------------------------------------------------
def monthly_standard_hours(weekly_hours: float) -> int:
    """월 소정근로시간 + 주휴시간 환산 (주 40시간이면 209시간)."""
    return int(round((weekly_hours + weekly_holiday_hours(weekly_hours)) * WEEKS_PER_MONTH))


@dataclass
class MinimumWageCheck:
    monthly_wage: int
    monthly_hours: int
    effective_hourly: float
    minimum_hourly: int
    minimum_monthly: int
    compliant: bool
    shortfall_monthly: int
    legal_basis: str = "최저임금법 제6조, 고용노동부고시 제2025-47호"


def check_minimum_wage(monthly_wage: int, weekly_hours: float = 40, rates: Rates = CURRENT) -> MinimumWageCheck:
    """월급이 최저임금 이상인지 확인. monthly_wage에는 최저임금 산입 대상 임금만 넣는다."""
    hours = monthly_standard_hours(weekly_hours)
    minimum_monthly = rates.minimum_hourly_wage * hours
    effective = monthly_wage / hours if hours else 0.0
    return MinimumWageCheck(
        monthly_wage=monthly_wage,
        monthly_hours=hours,
        effective_hourly=round(effective, 2),
        minimum_hourly=rates.minimum_hourly_wage,
        minimum_monthly=minimum_monthly,
        compliant=monthly_wage >= minimum_monthly,
        shortfall_monthly=max(0, minimum_monthly - monthly_wage),
    )


# ---------------------------------------------------------------------------
# 4대보험 (산재보험은 업종별 요율, 사업주 전액 부담이라 선택 입력)
# ---------------------------------------------------------------------------
@dataclass
class InsuranceBreakdown:
    pension: int
    health: int
    long_term_care: int
    employment: int
    industrial_accident: int
    total: int


@dataclass
class SocialInsuranceResult:
    taxable_base: int
    employee: InsuranceBreakdown
    employer: InsuranceBreakdown
    notes: list


def social_insurance(
    monthly_wage: int,
    nontaxable: int = 0,
    company_size: str = "under_150",
    industrial_accident_rate: float = 0.0,
    rates: Rates = CURRENT,
) -> SocialInsuranceResult:
    """월 보수 기준 4대보험료 (근로자·사업주 부담분).

    nontaxable: 비과세 소득(예: 식대 월 20만원 한도)은 보험료 산정에서 제외.
    industrial_accident_rate: 업종별 산재보험료율 (예: 0.0086). 모르면 0으로 두고 안내문 표시.
    """
    if company_size not in EMPLOYMENT_STABILITY_RATES:
        raise ValueError(f"company_size는 {list(EMPLOYMENT_STABILITY_RATES)} 중 하나여야 합니다.")

    base = max(0, monthly_wage - nontaxable)
    pension_base = base
    notes = []
    if rates.pension_base_min is not None:
        pension_base = max(pension_base, rates.pension_base_min)
    if rates.pension_base_max is not None:
        pension_base = min(pension_base, rates.pension_base_max)
    else:
        notes.append("국민연금 기준소득월액 상·하한이 설정되지 않아 미적용 상태입니다.")

    ltc_ratio = Decimal(str(rates.long_term_care_income_rate)) / Decimal(str(rates.health_total_rate))
    employer_emp_rate = Decimal(str(rates.employment_employer_unemployment)) + Decimal(
        str(EMPLOYMENT_STABILITY_RATES[company_size])
    )

    ee_pension = _premium(pension_base, rates.pension_employee)
    er_pension = _premium(pension_base, rates.pension_employer)
    ee_health = _premium(base, rates.health_employee)
    er_health = _premium(base, rates.health_employer)
    ee_ltc = _premium(ee_health, ltc_ratio)
    er_ltc = _premium(er_health, ltc_ratio)
    ee_emp = _premium(base, rates.employment_employee)
    er_emp = _premium(base, employer_emp_rate)
    er_ia = _premium(base, industrial_accident_rate)
    if industrial_accident_rate == 0:
        notes.append("산재보험료는 업종별 요율이 필요해 계산하지 않았습니다 (사업주 전액 부담).")

    employee = InsuranceBreakdown(ee_pension, ee_health, ee_ltc, ee_emp, 0, ee_pension + ee_health + ee_ltc + ee_emp)
    employer = InsuranceBreakdown(er_pension, er_health, er_ltc, er_emp, er_ia, er_pension + er_health + er_ltc + er_emp + er_ia)
    return SocialInsuranceResult(base, employee, employer, notes)


# ---------------------------------------------------------------------------
# 연장·야간·휴일 가산수당 (근로기준법 제56조, 5인 미만 사업장은 제11조로 적용 제외)
# ---------------------------------------------------------------------------
@dataclass
class OvertimePayResult:
    applies_premium: bool
    overtime_pay: int
    night_pay: int
    holiday_pay: int
    total: int
    explanation: str
    legal_basis: str = "근로기준법 제56조, 제11조, 같은 법 시행령 제7조 [별표 1]"


def overtime_pay(
    hourly_wage: float,
    overtime_hours: float = 0,
    night_hours: float = 0,
    holiday_hours: float = 0,
    employees: int = 5,
) -> OvertimePayResult:
    """가산수당 계산.

    - overtime_hours: 연장근로 시간 (1일 8시간·1주 40시간 초과분)
    - night_hours: 야간근로 시간 (22시~06시). 연장과 겹치면 양쪽 모두 입력하면 중복 가산됨.
    - holiday_hours: 휴일근로 시간 (8시간 이내 50%, 초과분 100% 가산)
    - employees: 상시 근로자 수. 5인 미만이면 가산수당 미적용(기본 시급만 지급).
    """
    premium = employees >= 5
    if premium:
        ot = hourly_wage * overtime_hours * 1.5
        night = hourly_wage * night_hours * 0.5  # 야간은 가산분만 (근로 자체 임금은 기본/연장에 포함)
        within8 = min(holiday_hours, 8)
        over8 = max(holiday_hours - 8, 0)
        hol = hourly_wage * (within8 * 1.5 + over8 * 2.0)
        explanation = "상시 5인 이상 사업장: 연장 1.5배, 야간 가산 0.5배, 휴일 8시간 이내 1.5배·초과 2배."
    else:
        ot = hourly_wage * overtime_hours
        night = 0.0
        hol = hourly_wage * holiday_hours
        explanation = "상시 5인 미만 사업장: 가산수당 규정이 적용되지 않아 일한 시간만큼 기본 시급으로 지급합니다."
    return OvertimePayResult(premium, int(round(ot)), int(round(night)), int(round(hol)), int(round(ot + night + hol)), explanation)


# ---------------------------------------------------------------------------
# LLM 도구 정의 (OpenAI 호환 function calling 스키마 — Ollama/vLLM 공통)
# ---------------------------------------------------------------------------
TOOL_FUNCTIONS = {
    "weekly_holiday_pay": weekly_holiday_pay,
    "check_minimum_wage": check_minimum_wage,
    "social_insurance": social_insurance,
    "overtime_pay": overtime_pay,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "weekly_holiday_pay",
            "description": "알바·직원의 주휴수당을 계산한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hourly_wage": {"type": "number", "description": "시급(원)"},
                    "weekly_hours": {"type": "number", "description": "1주 소정근로시간"},
                    "attended_all_days": {"type": "boolean", "description": "그 주 소정근로일 개근 여부"},
                },
                "required": ["hourly_wage", "weekly_hours"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_minimum_wage",
            "description": "월급이 2026년 최저임금 이상인지 확인한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_wage": {"type": "integer", "description": "최저임금 산입 대상 월급(원)"},
                    "weekly_hours": {"type": "number", "description": "1주 소정근로시간, 기본 40"},
                },
                "required": ["monthly_wage"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "social_insurance",
            "description": "월급 기준 4대보험료(근로자·사업주 부담분)를 계산한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_wage": {"type": "integer", "description": "월 급여 총액(원)"},
                    "nontaxable": {"type": "integer", "description": "비과세 금액(예: 식대 최대 200000)"},
                    "company_size": {
                        "type": "string",
                        "enum": list(EMPLOYMENT_STABILITY_RATES),
                        "description": "사업장 규모, 소상공인은 대부분 under_150",
                    },
                    "industrial_accident_rate": {"type": "number", "description": "업종별 산재보험료율(모르면 생략)"},
                },
                "required": ["monthly_wage"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "overtime_pay",
            "description": "연장·야간·휴일근로 수당을 계산한다. 5인 미만 사업장 여부를 반드시 반영한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hourly_wage": {"type": "number"},
                    "overtime_hours": {"type": "number"},
                    "night_hours": {"type": "number"},
                    "holiday_hours": {"type": "number"},
                    "employees": {"type": "integer", "description": "상시 근로자 수"},
                },
                "required": ["hourly_wage", "employees"],
            },
        },
    },
]


def run_tool(name: str, arguments: dict) -> dict:
    """LLM이 요청한 도구를 실행하고 JSON 직렬화 가능한 dict로 돌려준다."""
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"알 수 없는 도구: {name}"}
    try:
        return asdict(fn(**arguments))
    except (TypeError, ValueError) as e:
        return {"error": f"도구 인자 오류: {e}"}
