from fastapi import APIRouter, HTTPException, Depends
from auth.auth_dependency import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/kyc/{user_id}")
def audit_kyc(user_id: str, current_user=Depends(get_current_user)):
    return {"user_id": user_id, "status": "not_available", "message": "Audit trail is disabled in this build."}


@router.get("/identity/{user_id}")
def audit_identity(user_id: str, current_user=Depends(get_current_user)):
    return {"user_id": user_id, "status": "not_available", "message": "Audit trail is disabled in this build."}


@router.get("/loan/request/{loan_id}")
def audit_loan_request(loan_id: str, current_user=Depends(get_current_user)):
    return {"loan_id": loan_id, "status": "not_available", "message": "Audit trail is disabled in this build."}


@router.get("/loan/acceptance/{loan_id}")
def audit_loan_acceptance(loan_id: str, current_user=Depends(get_current_user)):
    return {"loan_id": loan_id, "status": "not_available", "message": "Audit trail is disabled in this build."}


@router.get("/agreement/execution/{loan_id}")
def audit_agreement_execution(loan_id: str, current_user=Depends(get_current_user)):
    return {"loan_id": loan_id, "status": "not_available", "message": "Audit trail is disabled in this build."}


@router.get("/transaction/{tx_id}")
def audit_transaction(tx_id: str, current_user=Depends(get_current_user)):
    return {"tx_id": tx_id, "status": "not_available", "message": "Audit trail is disabled in this build."}


@router.get("/repayments/{loan_id}")
def audit_repayments(loan_id: str, current_user=Depends(get_current_user)):
    return {"loan_id": loan_id, "status": "not_available", "message": "Audit trail is disabled in this build."}
