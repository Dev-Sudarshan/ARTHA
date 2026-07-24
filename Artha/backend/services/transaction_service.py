from schemas.transaction_schemas import TransactionReceiptSchema

from db.database import get_item, put_item, get_all_items

# ---- STORES REPLACED BY DB ----

PLATFORM_FEE_PERCENT = 3.0
LENDER_MAX_SHARE_PERCENT = 10


def process_fund_transfer(payload: TransactionReceiptSchema, lender_id: str):
    """
    Process fund transfer receipt. Enables LISTED -> ACTIVE transition (Auto-Accept).
    """

    loan_id = payload.loan_id

    # 1️⃣ Loan must exist
    loan = get_item("loans", loan_id)
    if not loan:
        raise Exception("Loan not found")

    borrower_id = loan["user_id"]
    
    # 0️⃣ Self-Lending Check
    if borrower_id == lender_id:
        raise Exception("Cannot lend to your own loan")

    # 2️⃣ Borrower/Lender exclusivity check
    lender_kyc = get_item("kyc", lender_id) or {}
    lender_bank = lender_kyc.get("bank_details", {})
    if lender_kyc.get("status") not in {"APPROVED", "VERIFIED"}:
        raise Exception("Verified KYC is required before lending")
    linked_account = lender_bank.get("account_number")
    if not (lender_bank.get("linked") or linked_account):
        raise Exception("Linked bank account is required before lending")
    if payload.sender_account != linked_account:
        raise Exception("Payment must be made from your linked bank account")
    lender_user = get_item("users", lender_id) or {}
    if lender_user.get("preferred_role", "borrower") != "lender":
        raise Exception("Only lender accounts can fund loans")

    lender_max_amount = max(1, int((loan.get("net_amount_received") or loan["amount"]) * LENDER_MAX_SHARE_PERCENT / 100))
    if payload.amount > lender_max_amount:
        raise Exception(f"Lenders can fund only up to 10% of this loan: NPR {lender_max_amount:,}")

    # 3️⃣ Borrower/Lender exclusivity check
    all_loans = get_all_items("loans")
    total_lended_so_far = 0
    for _, scan_loan in all_loans.items():
        if scan_loan.get("user_id") == lender_id and scan_loan.get("status") in ["LISTED", "ACTIVE", "AWAITING_SIGNATURE"]:
            raise Exception("Borrowers cannot lend money")
        if scan_loan.get("lender_id") == lender_id and scan_loan.get("status") != "REPAID":
            total_lended_so_far += scan_loan.get("funded_amount") or scan_loan["amount"]

    if total_lended_so_far + payload.amount > 500000:
        raise Exception("Lending limit (500,000) exceeded")

    # 3️⃣ Handle Status (Auto-Accept if LISTED)
    current_status = loan.get("status")
    
    if current_status == "LISTED":
        # Check if already funded (race condition check)
        if loan.get("lender_id"):
             raise Exception("Loan already assigned to a lender")
             
        # Transition to ACTIVE
        loan["status"] = "ACTIVE"
        loan["lender_id"] = lender_id
        loan["funded_amount"] = payload.amount
        # Use payload timestamp for consistency
        import datetime
        # If payload.timestamp is int (unix), convert? Schema says int.
        # But usually we store ISO strings in DB for readability? 
        # Existing code used payload.timestamp directly in record_loan_status.
        # Let's verify schema. Schema says int. 
        # Let's save it as handled below.
        
        # Save updated loan status immediately
        put_item("loans", loan_id, loan)
        
    elif current_status != "ACTIVE":
        raise Exception(f"Loan status is {current_status}, cannot fund.")

    # 4️⃣ Prevent duplicate funding (Check transactions table)
    existing_txn = get_item("transactions", loan_id)
    if existing_txn:
        raise Exception("Loan already funded")

    # 5️⃣ Initialize financial data if missing
    stats = get_item("financial_data", borrower_id)
    if not stats:
        stats = {
            "monthly_income": 0,
            "monthly_expense": 0,
            "total_transactions": 0,
            "failed_transactions": 0,
            "avg_transaction_amount": 0.0,
            "missed_payments": 0,
            "loan_outstanding": 0.0,
            "account_age_months": 0,
        }

    # Bank linking creates a financial-data record with statement metadata.
    # Complete that partial record before updating transaction counters.
    stats.setdefault("monthly_income", 0)
    stats.setdefault("monthly_expense", 0)
    stats.setdefault("total_transactions", 0)
    stats.setdefault("failed_transactions", 0)
    stats.setdefault("avg_transaction_amount", 0.0)
    stats.setdefault("missed_payments", 0)
    stats.setdefault("loan_outstanding", 0.0)
    stats.setdefault("account_age_months", 0)

    # 6️⃣ Update transaction counters
    stats["total_transactions"] += 1

    if not payload.success:
        stats["failed_transactions"] += 1
        put_item("financial_data", borrower_id, stats)
        raise Exception("Transaction failed")

    # 7️⃣ Store transaction receipt off-chain
    receipt_data = payload.dict()
    # Normalize timestamp to ISO string for storage
    ts_value = receipt_data.get("timestamp")
    if isinstance(ts_value, int):
        import datetime
        receipt_data["timestamp"] = datetime.datetime.fromtimestamp(ts_value).isoformat()
    elif hasattr(ts_value, "isoformat"):
        receipt_data["timestamp"] = ts_value.isoformat()
    
    put_item("transactions", loan_id, receipt_data)

    # 8️⃣ Update average transaction amount
    prev_total = stats["total_transactions"] - 1
    stats["avg_transaction_amount"] = (
        (stats["avg_transaction_amount"] * prev_total + payload.amount)
        / stats["total_transactions"]
    )

    # 9️⃣ Platform fee calculation
    fee_amount = payload.amount * (PLATFORM_FEE_PERCENT / 100)
    net_to_borrower = payload.amount - fee_amount

    # 10️⃣ Update outstanding loan amount
    stats["loan_outstanding"] += payload.amount
    
    # Save stats
    put_item("financial_data", borrower_id, stats)

    return {
        "message": "Fund transfer recorded successfully",
        "platform_fee": fee_amount,
        "net_to_borrower": net_to_borrower,
    }
