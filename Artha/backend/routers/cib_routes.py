from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.cib_service import run_cib_regulatory_screening

router = APIRouter(prefix="/cib", tags=["CIB Verification"])


class CIBVerifyRequest(BaseModel):
    citizenship_number: str


@router.post("/verify")
def verify_cib(payload: CIBVerifyRequest):
    """
    Exposes CIB Credit Verification endpoint.
    Accepts citizenship_number and returns risk assessment from CIB registry.
    """
    if not payload.citizenship_number or not payload.citizenship_number.strip():
        raise HTTPException(status_code=400, detail="Citizenship number is required.")

    try:
        result = run_cib_regulatory_screening(payload.citizenship_number.strip())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
