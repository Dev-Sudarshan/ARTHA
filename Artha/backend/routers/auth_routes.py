from fastapi import APIRouter, HTTPException, Depends
import traceback
from datetime import datetime
from random import randint
from auth.auth_service import (
    register_user,
    verify_registration_otp,
    login_user,
    logout_user,
    send_login_otp,
)

from auth.auth_dependency import get_current_user
from db.database import get_item, get_all_items, get_user_loan_summary, get_user_profile_data
from services.loan_service import get_credit_limit
from services.nchl_service import get_demo_nchl_account_for_mobile, process_nchl_statement_analysis
from services.credit_score_service import build_fixed_borrower_scorecard
from db.database import put_item

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_borrower_underwriting(phone: str, kyc_data: dict, active_role: str) -> dict | None:
    """Build borrower form permissions from the same pipeline used at submission."""
    if active_role != "borrower" or kyc_data.get("status") not in {"APPROVED", "VERIFIED"}:
        return None

    bank_details = kyc_data.get("bank_details", {})
    if not (bank_details.get("linked") or bank_details.get("account_number") or bank_details.get("account_no")):
        return None

    account_number = str(bank_details.get("account_number") or bank_details.get("account_no"))
    nchl_result = process_nchl_statement_analysis(account_number)
    scorecard = build_fixed_borrower_scorecard()
    put_item("credit_scores", phone, scorecard["credit_score"])
    kyc_data["underwriting"] = scorecard
    put_item("kyc", phone, kyc_data)
    return scorecard


def _has_linked_bank(kyc_data: dict) -> bool:
    bank_details = kyc_data.get("bank_details", {})
    return bool(bank_details.get("linked") or bank_details.get("account_number") or bank_details.get("account_no"))


@router.post("/register")
def register(payload: dict):
    """
    Register user and send OTP
    """
    try:
        register_user(
            phone=payload.get("phone"),
            password=payload.get("password"),
            first_name=payload.get("first_name") or payload.get("firstName"),
            middle_name=payload.get("middle_name") or payload.get("middleName"),
            last_name=payload.get("last_name") or payload.get("lastName"),
            dob=payload.get("dob"),
            preferred_role=payload.get("preferred_role") or payload.get("preferredRole") or payload.get("accountType"),
        )
        return {"message": "OTP sent to phone"}
    except ValueError as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-otp")
def verify_otp(payload: dict):
    """
    Verify OTP and log user in
    """
    try:
        token = verify_registration_otp(
            phone=payload.get("phone"),
            otp_code=payload.get("otp") or payload.get("otp_code"),
        )
        return {"token": token}
    except ValueError as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/send-login-otp")
def send_login_otp_route(payload: dict):
    """
    Send OTP for login
    """
    try:
        send_login_otp(payload["phone"])
        return {"message": "OTP sent"}
    except ValueError as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(payload: dict):
    """
    Login existing user
    """
    try:
        result = login_user(
            phone=payload.get("phone"),
            password=payload.get("password"),
            otp=payload.get("otp"),
        )
        return result
    except ValueError as e:
        traceback.print_exc()
        # If OTP required, we return 400 so frontend knows to show OTP field
        # But if invalid credentials, we usually return 401
        # The service raises 'Invalid credentials' or 'OTP verification required'
        # We can distinguish messages or just return 400 for everything except auth failure?
        # Standard: 401 for auth failure.
        if str(e) == "Invalid credentials":
            raise HTTPException(status_code=401, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
def logout(payload: dict):
    """
    Logout user
    """
    logout_user(payload["token"])
    return {"message": "Logged out successfully"}


@router.post("/bank-link")
def link_bank_account(payload: dict, current_user=Depends(get_current_user)):
    """Persist the demo bank credentials after KYC approval."""
    kyc_data = get_item("kyc", current_user) or {}
    if kyc_data.get("status") not in {"APPROVED", "VERIFIED"}:
        raise HTTPException(status_code=403, detail="Admin must approve KYC before linking a bank account")

    bank_name = str(payload.get("bank_name") or "").strip()
    mobile_number = str(payload.get("mobile_number") or "").strip()
    password = str(payload.get("password") or "")
    otp = str(payload.get("otp") or "")
    if not bank_name or not mobile_number or not password or otp != "123456":
        raise HTTPException(status_code=400, detail="Bank, mobile number, password, and OTP 123456 are required")

    account_number = get_demo_nchl_account_for_mobile(mobile_number) or f"DEMO-{randint(1000000000, 9999999999)}"
    nchl_result = process_nchl_statement_analysis(account_number)
    preferred_role = (get_item("users", current_user) or {}).get("preferred_role", "borrower")
    scorecard = build_fixed_borrower_scorecard(800) if preferred_role == "borrower" else None

    kyc_data["bank_details"] = {
        "linked": True,
        "bank_name": bank_name,
        "mobile_number": mobile_number,
        "password": password,
        "account_number": account_number,
        "linked_at": datetime.utcnow().isoformat(),
        "nchl_statement_metrics": nchl_result["metrics"],
    }
    kyc_data["underwriting"] = scorecard
    put_item("kyc", current_user, kyc_data)
    if scorecard:
        put_item("credit_scores", current_user, scorecard["credit_score"])
    put_item("financial_data", current_user, {
        "account_number": account_number,
        "bank_name": bank_name,
        "nchl_status": nchl_result["status"],
        "nchl_statement_metrics": nchl_result["metrics"],
        "underwriting_scorecard": scorecard,
        "updated_at": datetime.utcnow().isoformat(),
    })
    return {
        "message": "Bank account linked and NCHL statement data extracted",
        "bank_linked": True,
        "bank_name": bank_name,
        "account_number": account_number,
        "nchl_status": nchl_result["status"],
        "nchl_statement_metrics": nchl_result["metrics"],
        "underwriting": scorecard,
        "credit_score": scorecard["credit_score"] if scorecard else None,
    }


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    """Return live user profile info based on session token — single DB connection."""
    phone = current_user

    # Single connection fetches user + kyc + credit_score + loan summary
    profile = get_user_profile_data(phone)
    user = profile["user"]
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    kyc_data = profile["kyc"] or {}
    kyc_status = kyc_data.get("status") or "INCOMPLETE"
    kyc_verified = kyc_status in {"APPROVED", "VERIFIED"}
    bank_details = kyc_data.get("bank_details", {})
    bank_linked = _has_linked_bank(kyc_data)

    preferred_role = user.get("preferred_role") or user.get("preferredRole") or "borrower"
    underwriting = _get_borrower_underwriting(phone, kyc_data, preferred_role)
    borrowing_limit = underwriting["request_limit_cap"] if underwriting else 0
    is_borrower = preferred_role != "lender"
    credit_score = underwriting["credit_score"] if underwriting else (profile["credit_score"] if bank_linked else 0)

    return {
        "firstName": user.get("first_name") or user.get("firstName") or "",
        "middleName": user.get("middle_name") or user.get("middleName"),
        "lastName": user.get("last_name") or user.get("lastName") or "",
        "phone": user.get("phone") or phone,
        "dob": user.get("dob"),
        "createdAt": user.get("created_at"),
        "preferredRole": user.get("preferred_role") or user.get("preferredRole") or "borrower",
        "kycVerified": kyc_verified,
        "kycStatus": kyc_status,
        "creditScore": credit_score if is_borrower else None,
        "activeRole": profile["active_role"],
        "totalLended": profile["total_lended"],
        "totalBorrowed": profile["total_borrowed"],
        "borrowingLimit": borrowing_limit,
        "borrowerClass": underwriting["borrower_class"] if underwriting else None,
        "requestLimitCap": borrowing_limit,
        "interestRateFloor": underwriting["interest_rate_floor"] if underwriting else None,
        "formPermissions": underwriting["form_permissions"] if underwriting else None,
        "bankLinked": bank_linked,
        "bankName": bank_details.get("bank_name"),
        "bankAccountNumber": bank_details.get("account_number"),
        "nchlStatementMetrics": bank_details.get("nchl_statement_metrics"),
        "underwriting": underwriting or kyc_data.get("underwriting"),
    }
