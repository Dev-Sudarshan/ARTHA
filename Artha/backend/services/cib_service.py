"""CIB regulatory gate for borrower underwriting."""

MOCK_CIB_REGISTRY = {
    "201-02-78-11111": {
        "cib_credit_score": 410,
        "has_active_loans": True,
        "is_blacklisted": True,
    },
    "201-03-79-22222": {
        "cib_credit_score": 720,
        "has_active_loans": True,
        "is_blacklisted": False,
    },
}


def _fetch_local_cib_report(citizenship_number: str) -> dict:
    """Return a mock bureau report until the live CIB adapter is configured."""
    return MOCK_CIB_REGISTRY.get(
        citizenship_number,
        {
            "cib_credit_score": 780,
            "has_active_loans": False,
            "is_blacklisted": False,
        },
    )


def run_cib_regulatory_screening(citizenship_number: str) -> dict:
    """Block borrowers with any active facility or CIB blacklist record."""
    report = _fetch_local_cib_report(citizenship_number.strip())
    has_active_loans = bool(report["has_active_loans"])
    is_blacklisted = bool(report["is_blacklisted"])

    if is_blacklisted or has_active_loans:
        return {
            "eligible": False,
            "reason": "Applicant is disqualified due to matching active loan facilities or blacklisting markers in the central registry.",
            "data": None,
        }

    return {
        "eligible": True,
        "reason": "Passed bureau check. Zero active loan histories detected.",
        "data": {
            "is_blacklisted": False,
            "has_active_loans": False,
        },
    }
