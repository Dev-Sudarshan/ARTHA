"""Compatibility stub for certificate generation."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi import Depends

from admin.admin_auth import get_current_admin

router = APIRouter()


@router.get("/certificate/{loan_id}")
async def generate_blockchain_certificate(
    loan_id: str,
    admin=Depends(get_current_admin)
):
    raise HTTPException(status_code=410, detail="Certificate generation is disabled in this build")
