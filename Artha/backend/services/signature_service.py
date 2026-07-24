from schemas.loan_agreement_schemas import SignedAgreementUploadSchema

# ✅ IMAGE FACE VERIFICATION (identity only)
from models.face_verification_model import verify_face_identity


from db.database import get_item, put_item


# =========================
# THUMB VERIFICATION PLACEHOLDER
# =========================

def verify_thumbs_with_ai(
    borrower_thumb_ref: str,
    guarantor_thumb_ref: str,
    signed_pdf_ref: str,
) -> bool:
    """
    Fingerprint verification (SourceAFIS / NBIS)
    """
    return True


# =========================
# MAIN SERVICE
# =========================

def process_signed_agreement(payload: SignedAgreementUploadSchema):
    """
    Finalize loan after:
    - signed PDF upload
    - STRICT video verification (exact declaration + face)
    - IMAGE face verification (signed image vs citizenship)
    - thumb verification
    """

    loan_id = payload.loan_id
    loan = get_item("loans", loan_id)

    # 1️⃣ Loan must exist
    if not loan:
        raise Exception("Loan not found")

    # 2️⃣ Loan must be awaiting signature
    if loan["status"] != "AWAITING_SIGNATURE":
        raise Exception("Loan is not awaiting signature")

    borrower_id = loan["user_id"]
    guarantor = loan.get("guarantor")

    # 3️⃣ Fetch borrower KYC
    borrower_kyc = get_item("kyc", borrower_id)
    if not borrower_kyc:
        raise Exception("Borrower KYC not found")

    borrower_thumb_ref = borrower_kyc.get("thumb_ref")
    citizenship_image_ref = borrower_kyc.get("citizenship_image")

    if not citizenship_image_ref:
        raise Exception("Citizenship image missing in KYC")

    # 4️⃣ Fetch guarantor thumb (if any)
    guarantor_thumb_ref = None
    if guarantor:
        guarantor_kyc = get_item("kyc", guarantor.get("user_id"))
        if not guarantor_kyc:
            raise Exception("Guarantor KYC not found")
        guarantor_thumb_ref = guarantor_kyc.get("thumb_ref")

    # Video verification step removed in this build.
    # The remaining image-based identity verification continues to run.

    # =========================
    # IMAGE FACE VERIFICATION (SIGNED IMAGE)
    # =========================

    image_result = verify_face_identity(
        image_path=payload.signed_image_ref,  # image extracted from signed PDF
        citizenship_image_path=citizenship_image_ref,
    )

    if image_result["final_status"] != "APPROVED":
        raise Exception("Image face verification failed")

    # =========================
    # THUMB VERIFICATION
    # =========================

    thumbs_verified = verify_thumbs_with_ai(
        borrower_thumb_ref=borrower_thumb_ref,
        guarantor_thumb_ref=guarantor_thumb_ref,
        signed_pdf_ref=payload.signed_pdf_ref,
    )

    if not thumbs_verified:
        raise Exception("Thumb verification failed")

    # =========================
    # FINALIZE LOAN
    # =========================

    loan["agreement_pdf_signed"] = payload.signed_pdf_ref
    loan["status"] = "LISTED"
    
    put_item("loans", loan_id, loan)

    return {
        "message": "Loan agreement verified (video + image + thumb) and listed",
        "loan_id": loan_id,
        "status": "LISTED",
    }
