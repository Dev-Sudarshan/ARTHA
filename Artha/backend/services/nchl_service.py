"""NCHL statement metrics extractor used after the CIB borrower gate passes."""

MOCK_NCHL_STATEMENTS = {
    "NCHL-9763470096": {
        "account_holder": "Demo Borrower 9763470096",
        "account_number": "NCHL-9763470096",
        "avg_monthly_salary": 112000.0,
        "salary_transaction_count": 6,
        "average_monthly_balance": 72000.0,
        "bounced_cheque_count": 0,
        "digital_payment_velocity": 72,
        "total_monthly_debits": 52000.0,
    },
    "DEFAULT": {
        "avg_monthly_salary": 85000.0,
        "salary_transaction_count": 3,
        "average_monthly_balance": 35000.0,
        "bounced_cheque_count": 0,
        "digital_payment_velocity": 48,
        "total_monthly_debits": 45000.0,
    }
}


def get_demo_nchl_account_for_mobile(mobile_number: str) -> str | None:
    """Return a deterministic linked demo account for seeded mobile banking users."""
    if str(mobile_number or "").strip() == "9763470096":
        return "NCHL-9763470096"
    return None


def process_nchl_statement_analysis(account_number: str) -> dict:
    """Extract raw behavioral metrics only; scoring and tiering happen downstream."""
    if not account_number or not account_number.strip():
        raise ValueError("Account number is required for NCHL statement analysis.")

    metrics = MOCK_NCHL_STATEMENTS.get(account_number.strip(), MOCK_NCHL_STATEMENTS["DEFAULT"])
    return {"status": "DATA_EXTRACTED", "metrics": dict(metrics)}
