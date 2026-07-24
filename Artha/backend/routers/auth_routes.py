from fastapi import APIRouter, HTTPException, Depends
import traceback
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
from services.cib_service import run_cib_regulatory_screening
from services.nchl_service import process_nchl_statement_analysis
from services.credit_score_service import calculate_credit_score, classify_borrower
from db.database import put_item

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_borrower_underwriting(phone: str, kyc_data: dict, active_role: str) -> dict | None:
    """Build borrower form permissions from the same pipeline used at submission."""
    if active_role == "lender" or kyc_data.get("status") not in {"APPROVED", "VERIFIED"}:
        return None

    citizenship_number = str(
        kyc_data.get("id_documents", {}).get("id_details", {}).get("id_number", "")
    ).strip()
    cib_result = run_cib_regulatory_screening(citizenship_number)
    if not cib_result["eligible"]:
        classification = classify_borrower(0)
        return {"credit_score": 0, "verdict": "DECLINED", **classification}

    bank_details = kyc_data.get("bank_details", {})
    account_number = str(bank_details.get("account_number") or bank_details.get("account_no") or phone)
    nchl_result = process_nchl_statement_analysis(account_number)
    scorecard = calculate_credit_score(nchl_result["metrics"])
    put_item("credit_scores", phone, scorecard["credit_score"])
    put_item("underwriting_profiles", phone, scorecard)
    return scorecard


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
    kyc_verified = kyc_status == "APPROVED"

    underwriting = _get_borrower_underwriting(phone, kyc_data, profile["active_role"])
    borrowing_limit = underwriting["request_limit_cap"] if underwriting else 0

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
        "creditScore": underwriting["credit_score"] if underwriting else profile["credit_score"],
        "activeRole": profile["active_role"],
        "totalLended": profile["total_lended"],
        "totalBorrowed": profile["total_borrowed"],
        "borrowingLimit": borrowing_limit,
        "borrowerClass": underwriting["borrower_class"] if underwriting else None,
        "requestLimitCap": borrowing_limit,
        "interestRateFloor": underwriting["interest_rate_floor"] if underwriting else None,
        "formPermissions": underwriting["form_permissions"] if underwriting else None,
    }
