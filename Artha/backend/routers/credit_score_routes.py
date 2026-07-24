from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.credit_score_service import calculate_credit_score

router = APIRouter(prefix="/credit-score", tags=["Credit Scorecard"])


class CreditScoreRequest(BaseModel):
    metrics: dict
    tenure_months: int = Field(default=12, gt=0)


@router.post("/evaluate")
def evaluate_credit_score(payload: CreditScoreRequest):
    try:
        return calculate_credit_score(payload.metrics, payload.tenure_months)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
