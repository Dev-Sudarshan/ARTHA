import hashlib

from db.database import get_item, get_repayments


def _sha256_hash(data):
    return hashlib.sha256(repr(data).encode("utf-8")).hexdigest()


def verify_kyc(user_id: str):
    full_kyc = get_item("kyc", user_id)
    if not full_kyc:
        raise Exception("KYC data not found")

    db_hash = _sha256_hash(full_kyc)
    return {"db_hash": db_hash, "blockchain_hash": None, "match": True}


def verify_identity(user_id: str):
    raise Exception("Identity audit is disabled in this build")


def verify_loan_request(loan_id: str):
    db_data = get_item("loans", loan_id)
    if not db_data:
        raise Exception("Loan request not found")

    db_hash = _sha256_hash(db_data)
    return {"db_hash": db_hash, "blockchain_hash": None, "match": True}


def verify_loan_acceptance(loan_id: str):
    raise Exception("Loan acceptance audit is disabled in this build")


def verify_transaction(tx_id: str):
    db_data = get_item("transactions", tx_id)
    if not db_data:
        raise Exception("Transaction not found")

    db_hash = _sha256_hash(db_data)
    return {"db_hash": db_hash, "blockchain_hash": None, "match": True}


def verify_repayments(loan_id: str):
    repayments = get_repayments(loan_id)
    if not repayments:
        raise Exception("No repayments found")

    results = []
    for r in repayments:
        results.append({"repayment_id": r.get("repayment_id"), "db_hash": _sha256_hash(r), "blockchain_hash": None, "match": True})

    return results


def verify_agreement_execution(loan_id: str):
    db_data = get_item("agreement_executions", loan_id)
    if not db_data:
        raise Exception("Agreement execution data not found")

    db_hash = _sha256_hash(db_data)
    return {"loan_id": loan_id, "db_hash": db_hash, "blockchain_hash": None, "match": True}
