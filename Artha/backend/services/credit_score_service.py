"""Bank-grade scorecard and affordability analysis for clean borrowers."""

from math import pow
from typing import Any, Mapping


POLICY_MAX_LIMIT = 500_000
MAX_PAYMENT_TO_FDI_RATIO = 0.35


def classify_borrower(credit_score: int) -> dict:
    """Map a score to the platform's borrower class and form permissions."""
    if credit_score >= 750:
        borrower_class, limit, rate, message = (
            "CLASS_A_PLATINUM", 500_000, "12.0%",
            "User cleared for maximum limit request creation.",
        )
    elif credit_score >= 650:
        borrower_class, limit, rate, message = (
            "CLASS_B_GOLD", 250_000, "13.0%",
            "User cleared for standard request creation.",
        )
    elif credit_score >= 550:
        borrower_class, limit, rate, message = (
            "CLASS_C_SILVER", 100_000, "14.0%",
            "User cleared for micro-credit request creation.",
        )
    elif credit_score >= 400:
        borrower_class, limit, rate, message = (
            "CLASS_D_BRONZE", 30_000, "15.0%",
            "User is restricted to a small single loan request.",
        )
    else:
        borrower_class, limit, rate, message = (
            "CLASS_E", 0, None, "Not Eligible to Borrow",
        )

    return {
        "borrower_class": borrower_class,
        "request_limit_cap": limit,
        "interest_rate_floor": rate,
        "form_permissions": {
            "can_create_request": limit > 0,
            "max_allowed_input_value": limit,
            "validation_message": message,
        },
    }


def build_fixed_borrower_scorecard(credit_score: int = 800) -> dict:
    """Demo policy: verified borrowers with linked bank accounts receive a fixed score."""
    classification = classify_borrower(credit_score)
    result = {
        "credit_score": credit_score,
        "risk_tier": classification["borrower_class"],
        "max_eligible_limit": classification["request_limit_cap"],
        "interest_rate": classification["interest_rate_floor"],
        "verdict": "APPROVED",
        "underwriting_analytics": {
            "cash_utilization_percent": "0.0%",
            "monthly_free_cashflow": 0.0,
            "calculated_dscr_buffer": 0.0,
        },
    }
    result.update(classification)
    return result


def _loan_principal_for_payment(monthly_payment: float, annual_rate: float, months: int) -> int:
    """Calculate the principal whose amortized EMI equals the payment capacity."""
    if monthly_payment <= 0:
        return 0
    monthly_rate = annual_rate / 1200
    if monthly_rate == 0:
        return int(monthly_payment * months)
    factor = pow(1 + monthly_rate, months)
    return int(monthly_payment * (factor - 1) / (monthly_rate * factor))


def calculate_credit_score(metrics: Mapping[str, Any], tenure_months: int = 12) -> dict:
    """Score raw NCHL observations and size a loan against disposable income."""
    required_fields = {
        "avg_monthly_salary", "average_monthly_balance", "bounced_cheque_count",
        "digital_payment_velocity", "total_monthly_debits",
    }
    missing = required_fields.difference(metrics)
    if missing:
        raise ValueError(f"Missing NCHL metrics: {', '.join(sorted(missing))}.")
    if tenure_months <= 0:
        raise ValueError("Loan tenure must be positive.")

    salary = float(metrics["avg_monthly_salary"])
    balance = float(metrics["average_monthly_balance"])
    bounced_cheques = int(metrics["bounced_cheque_count"])
    payment_velocity = float(metrics["digital_payment_velocity"])
    monthly_debits = float(metrics["total_monthly_debits"])
    if salary <= 0:
        raise ValueError("Average monthly salary must be greater than zero.")

    monthly_free_cashflow = salary - monthly_debits
    utilization = max(monthly_debits / salary, 0.0)
    cash_utilization_percent = f"{utilization * 100:.1f}%"
    max_monthly_emi = max(monthly_free_cashflow, 0.0) * MAX_PAYMENT_TO_FDI_RATIO

    if bounced_cheques > 0:
        result = {
            "credit_score": 0, "risk_tier": "KNOCKOUT", "max_eligible_limit": 0,
            "interest_rate": None, "verdict": "DECLINED",
            "underwriting_analytics": {
                "cash_utilization_percent": cash_utilization_percent,
                "monthly_free_cashflow": monthly_free_cashflow,
                "calculated_dscr_buffer": 0.0,
            },
        }
        result.update(classify_borrower(0))
        return result

    # Weighted components: income 40%, liquidity 20%, traceability 15%, burn rate 25%.
    income_component = min(salary / 100_000, 1.0) * 400
    liquidity_component = min(balance / 50_000, 1.0) * 200
    traceability_component = min(payment_velocity / 60, 1.0) * 150
    burn_rate_component = max(1 - min(utilization, 1.0), 0.0) * 250
    raw_score = income_component + liquidity_component + traceability_component + burn_rate_component
    credit_score = max(300, min(850, round(300 + raw_score * 0.69)))

    if monthly_free_cashflow <= 0 or credit_score < 400:
        risk_tier, interest_rate, verdict = "HIGH_RISK", None, "DECLINED"
    else:
        risk_tier, verdict = "APPROVED", "APPROVED"

    classification = classify_borrower(credit_score)
    if verdict == "APPROVED":
        risk_tier = classification["borrower_class"]
        interest_rate = float(classification["interest_rate_floor"].rstrip("%"))
    else:
        classification = classify_borrower(0)

    result = {
        "credit_score": credit_score,
        "risk_tier": risk_tier,
        "max_eligible_limit": classification["request_limit_cap"],
        "interest_rate": f"{interest_rate:.1f}%" if interest_rate is not None else None,
        "verdict": verdict,
        "underwriting_analytics": {
            "cash_utilization_percent": cash_utilization_percent,
            "monthly_free_cashflow": monthly_free_cashflow,
            "calculated_dscr_buffer": round(monthly_free_cashflow / max_monthly_emi, 2) if max_monthly_emi else 0.0,
        },
    }
    result.update(classification)
    return result
