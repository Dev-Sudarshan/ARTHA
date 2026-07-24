from pydantic import BaseModel
from typing import Optional


class RepaymentSchema(BaseModel):
    loan_id: str

    repayment_id: str
    amount: float

    repayment_type: str    # "PARTIAL" or "FULL"
    source_account: Optional[str] = None

    paid_by: str           # borrower user_id
    timestamp: int
