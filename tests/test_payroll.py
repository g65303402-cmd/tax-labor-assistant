from app.tools import payroll as p


def test_monthly_standard_hours_40h_is_209():
    assert p.monthly_standard_hours(40) == 209


def test_minimum_monthly_wage_2026():
    r = p.check_minimum_wage(2_156_880)
    assert r.minimum_monthly == 2_156_880
    assert r.compliant


def test_minimum_wage_violation():
    r = p.check_minimum_wage(2_100_000)
    assert not r.compliant
    assert r.shortfall_monthly == 56_880


def test_weekly_holiday_pay_full_time():
    r = p.weekly_holiday_pay(10_320, 40)
    assert r.eligible and r.holiday_hours == 8
    assert r.weekly_holiday_pay == 82_560


def test_weekly_holiday_pay_part_time_20h():
    r = p.weekly_holiday_pay(10_320, 20)
    assert r.holiday_hours == 4
    assert r.weekly_holiday_pay == 41_280


def test_weekly_holiday_pay_under_15h():
    r = p.weekly_holiday_pay(10_320, 14)
    assert not r.eligible and r.weekly_holiday_pay == 0


def test_weekly_holiday_pay_absent():
    assert not p.weekly_holiday_pay(10_320, 40, attended_all_days=False).eligible


def test_social_insurance_3m():
    r = p.social_insurance(3_000_000)
    assert r.employee.pension == 142_500      # 4.75%
    assert r.employee.health == 107_850       # 3.595%
    assert r.employee.long_term_care == 14_170  # 107,850 × 0.9448/7.19 = 14,172 → 10원 절사
    assert r.employee.employment == 27_000    # 0.9%
    assert r.employer.employment == 34_500    # 0.9% + 0.25%


def test_social_insurance_no_float_error():
    # 회귀 테스트: float 계산 시 3,000,000 × 0.009 = 26,999.99… → 26,990원으로 잘못 절사됐었음
    for wage in (1_000_000, 2_000_000, 3_000_000, 5_000_000):
        assert p.social_insurance(wage).employee.employment == wage * 9 // 1000


def test_social_insurance_excludes_nontaxable_meal():
    r = p.social_insurance(3_200_000, nontaxable=200_000)
    assert r.taxable_base == 3_000_000


def test_overtime_under_5_employees_has_no_premium():
    r = p.overtime_pay(10_320, overtime_hours=10, employees=4)
    assert not r.applies_premium
    assert r.overtime_pay == 103_200


def test_overtime_5_plus_employees():
    r = p.overtime_pay(10_000, overtime_hours=2, night_hours=2, holiday_hours=10, employees=5)
    assert r.overtime_pay == 30_000
    assert r.night_pay == 10_000
    assert r.holiday_pay == 8 * 15_000 + 2 * 20_000


def test_run_tool_handles_bad_args():
    assert "error" in p.run_tool("weekly_holiday_pay", {"wrong": 1})
    assert "error" in p.run_tool("nope", {})
