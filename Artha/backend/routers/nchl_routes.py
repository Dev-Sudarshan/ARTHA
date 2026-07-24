from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.nchl_service import process_nchl_statement_analysis

router = APIRouter(prefix="/nchl", tags=["NCHL Statement Analysis"])


class NCHLStatementRequest(BaseModel):
    account_number: str


@router.post("/analyze")
def analyze_statement(payload: NCHLStatementRequest):
    try:
        return process_nchl_statement_analysis(payload.account_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
