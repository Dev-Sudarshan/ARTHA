# backend/routers/borrower_router.py
from fastapi import APIRouter, HTTPException
# Note: Adjust 'backend.' prefix depending on how your main app sets its PYTHONPATH
from services.cib_service import run_cib_regulatory_screening

router = APIRouter(
    prefix="/api/v1/borrower",
    tags=["Borrower Risk Verification"]
)

@router.get("/check-cib/{citizenship_no}")
def check_borrower_cib(citizenship_no: str):
    """
    Onboarding gateway endpoint that checks a borrower's citizenship 
    number against the integrated CIB credit index registry.
    """
    try:
        result = run_cib_regulatory_screening(citizenship_no)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Risk Engine Error: {str(e)}")
