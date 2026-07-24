from schemas.kyc_schemas import (
    KYCPageOneSchema,
    KYCPageTwoSchema,
    KYCPageThreeSchema,
)

from models.citizenship_ocr_model import verify_citizenship_card

from db.database import get_item, put_item

import os
from urllib.parse import urlparse


def _resolve_upload_ref(ref: str) -> str:
    """Resolve frontend-provided refs (e.g. '/static/uploads/x.png' or full URLs) to local disk paths.

    The AI pipeline expects filesystem paths. The upload API returns browser URLs under /static/uploads.
    """
    if not ref:
        return ref

    text = str(ref).strip().replace('\\', '/').replace('\\\\', '/')
    # If it's a full URL, extract only the path portion
    if text.startswith('http://') or text.startswith('https://'):
        try:
            text = urlparse(text).path or text
        except Exception:
            pass

    # Normalize leading slash variants
    if text.startswith('static/uploads/'):
        filename = text.split('static/uploads/', 1)[1]
    elif text.startswith('/static/uploads/'):
        filename = text.split('/static/uploads/', 1)[1]
    else:
        # Already a filesystem path or non-static reference
        return ref

    backend_dir = os.path.dirname(__file__)
    static_dir = os.path.abspath(os.path.join(backend_dir, '..', 'static'))
    uploads_dir = os.path.join(static_dir, 'uploads')
    return os.path.join(uploads_dir, filename)


# ---- CREDIT SCORE CONSTANT ----
INITIAL_CREDIT_SCORE = 0

# ---- KYC STAGES ----
STAGE_BASIC = "BASIC_INFO_SUBMITTED"
STAGE_ID = "ID_ANALYSIS_RUNNING"
STAGE_VIDEO = "VIDEO_ANALYSIS_RUNNING"
STAGE_DONE = "FINALIZED"


# =========================
# PAGE 1 — BASIC INFO
# =========================

def submit_basic_info(payload: KYCPageOneSchema):
    """
    Page 1: Store basic info & address
    """
    user_id = payload.user_id

    kyc_data = get_item("kyc", user_id) or {}

    payload_dict = payload.dict()
    kyc_data["basic_info"] = payload_dict["basic_info"]
    kyc_data["permanent_address"] = payload_dict["permanent_address"]
    kyc_data["temporary_address"] = payload_dict["temporary_address"]
    kyc_data["stage"] = STAGE_BASIC
    kyc_data["status"] = "PENDING"

    put_item("kyc", user_id, kyc_data)


# =========================
# PAGE 2 — ID DOCUMENTS + OCR
# =========================

def submit_id_documents(payload: KYCPageTwoSchema):
    """
    Page 2:
    - Store ID documents only
    - NO verification yet (verification happens in Page 3 after all data is collected)
    """
    user_id = payload.user_id
    print(f"[KYC DEBUG] Starting Step 2 for user: {user_id}")

    kyc_data = get_item("kyc", user_id)
    if not kyc_data or "basic_info" not in kyc_data:
        print("[KYC DEBUG] Error: Basic info missing in DB")
        raise Exception("Basic KYC info not submitted")

    # ---- Store ID documents without running verification ----
    front_img = _resolve_upload_ref(payload.id_images.front_image_ref)
    back_img = _resolve_upload_ref(payload.id_images.back_image_ref)
    print(f"[KYC DEBUG] Image paths stored: {front_img}, {back_img}")

    kyc_data["id_documents"] = payload.dict()
    kyc_data["stage"] = STAGE_ID

    put_item("kyc", user_id, kyc_data)
    print(f"[KYC DEBUG] Step 2 complete for {user_id} - documents stored, verification deferred to final step")

    return {
        "user_id": user_id,
        "message": "ID documents saved. Complete final step to verify.",
    }


import threading

# =========================
# PAGE 3 — VIDEO + FINAL KYC (Actually Face Photo Match)
# =========================

def submit_declaration_video(payload: KYCPageThreeSchema):
    """
    Page 3 (FINAL STEP):
    - Save declaration data immediately and return fast
    - AI verification (OCR, face match, liveness) runs in background thread
    """
    user_id = payload.user_id
    print(f"[KYC DEBUG] Starting Step 3 for user: {user_id}")

    kyc_data = get_item("kyc", user_id)
    if not kyc_data or "id_documents" not in kyc_data:
        print("[KYC DEBUG] Error: ID documents missing in DB")
        raise Exception("ID documents (Page 2) not submitted")

    if not kyc_data.get("basic_info"):
        raise Exception("Basic info (Page 1) not submitted")

    live_photo_ref = _resolve_upload_ref(payload.declaration_video.selfie_image_ref)
    live_video_ref = _resolve_upload_ref(payload.declaration_video.video_ref)

    if not live_photo_ref and not live_video_ref:
        raise Exception("Selfie image or video not provided")

    # ---- SAVE DECLARATION DATA IMMEDIATELY ----
    kyc_data["declaration"] = payload.dict()
    kyc_data["stage"] = STAGE_VIDEO
    kyc_data["status"] = "PROCESSING"
    put_item("kyc", user_id, kyc_data)

    # ---- Initialize borrower credit score ONCE ----
    user_data = get_item("users", user_id) or {}
    existing_score = get_item("credit_scores", user_id)
    if user_data.get("preferred_role", "borrower") == "borrower" and existing_score is None:
        put_item("credit_scores", user_id, INITIAL_CREDIT_SCORE)

    # ---- LAUNCH BACKGROUND VERIFICATION ----
    thread = threading.Thread(
        target=_run_verification_background,
        args=(user_id,),
        daemon=True,
    )
    thread.start()
    print(f"[KYC DEBUG] Background verification launched for {user_id}")

    return {
        "user_id": user_id,
        "kyc_status": "PROCESSING",
        "message": "KYC submitted successfully. Verification is running in the background.",
    }


def _run_verification_background(user_id: str):
    """
    Runs ALL AI verification in a background thread so the HTTP response is instant.
    """
    try:
        import time as _time
        _t_total = _time.time()
        print(f"[KYC BG] Starting background verification for {user_id}")
        kyc_data = get_item("kyc", user_id)
        if not kyc_data:
            print(f"[KYC BG] ERROR: No KYC data found for {user_id}")
            return

        basic_info = kyc_data["basic_info"]
        front_image_ref = _resolve_upload_ref(kyc_data["id_documents"]["id_images"]["front_image_ref"])
        back_image_ref = _resolve_upload_ref(kyc_data["id_documents"]["id_images"]["back_image_ref"])
        live_photo_ref = _resolve_upload_ref(kyc_data["declaration"]["declaration_video"]["selfie_image_ref"])
        live_video_ref = _resolve_upload_ref(kyc_data["declaration"]["declaration_video"].get("video_ref"))

        print(f"[KYC BG] Resolved paths:")
        print(f"[KYC BG]   front_image = {front_image_ref} (exists={os.path.isfile(front_image_ref) if front_image_ref else 'N/A'})")
        print(f"[KYC BG]   back_image  = {back_image_ref} (exists={os.path.isfile(back_image_ref) if back_image_ref else 'N/A'})")
        print(f"[KYC BG]   live_photo  = {live_photo_ref} (exists={os.path.isfile(live_photo_ref) if live_photo_ref else 'N/A'})")
        if back_image_ref and os.path.isfile(back_image_ref):
            print(f"[KYC BG]   back_image size = {os.path.getsize(back_image_ref)} bytes")

        # ============================================================
        # STEP 1: OCR VERIFICATION (citizenship card)
        # ============================================================
        _t1 = _time.time()
        print("[KYC BG] === STEP 1: Running OCR verification ===")

        full_name = " ".join(
            filter(
                None,
                [
                    basic_info.get("first_name"),
                    basic_info.get("middle_name"),
                    basic_info.get("last_name"),
                ],
            )
        )
        dob = basic_info.get("date_of_birth")
        citizenship_no = kyc_data["id_documents"]["id_details"]["id_number"]

        ai_results = {
            "gov_id_verified": False,
            "name_match": False,
            "dob_match": False,
            "citizenship_no_match": False,
            "thumbprint_detected": False,
            "face_detected_on_card": False,
            "ocr_error": None,
        }

        try:
            from models.citizenship_ocr_model import verify_citizenship_card, extract_thumbprint, detect_face_on_card

            ocr_result = verify_citizenship_card(
                image_path=back_image_ref,
                input_full_name=full_name,
                input_dob=dob,
                input_citizenship_no=citizenship_no,
            )
            print(f"[KYC BG] OCR Result: {ocr_result}")

            # Store the extracted OCR data in the database
            kyc_data["id_documents"]["ocr_extracted"] = ocr_result.get("extracted_fields", {})
            put_item("kyc", user_id, kyc_data)  # Save immediately so OCR data is available

            thumbprint_detected = extract_thumbprint(back_image_ref)
            face_detected = detect_face_on_card(front_image_ref)
            print(f"[KYC BG] Detections: Thumb:{thumbprint_detected}, Face:{face_detected}")

            ai_results.update(
                {
                    "gov_id_verified": ocr_result.get("final_ocr_status") == "PASSED",
                    "name_match": bool(ocr_result.get("name_match")),
                    "dob_match": bool(ocr_result.get("dob_match")),
                    "citizenship_no_match": bool(ocr_result.get("citizenship_no_match")),
                    "thumbprint_detected": bool(thumbprint_detected),
                    "face_detected_on_card": bool(face_detected),
                }
            )
        except Exception as ai_err:
            print(f"[KYC BG] OCR verification failed (non-blocking): {ai_err}")
            ai_results["ocr_error"] = str(ai_err)

        print(f"[KYC BG] STEP 1 (OCR) took {_time.time() - _t1:.1f}s")

        # ============================================================
        # STEP 1.5: PEP / SANCTIONS / CFT SCREENING (OpenSanctions)
        # ============================================================
        _t15 = _time.time()
        print("[KYC BG] === STEP 1.5: Running PEP / Sanctions / CFT screening ===")

        # Prefer the OCR-extracted name (official document name) over user-entered name
        ocr_extracted = kyc_data.get("id_documents", {}).get("ocr_extracted", {})
        screening_name = ocr_extracted.get("full_name") or full_name
        screening_id = ocr_extracted.get("citizenship_certificate_number") or citizenship_no
        screening_dob = ocr_extracted.get("date_of_birth") or dob

        print(f"[KYC BG] Screening with: name='{screening_name}', id='{screening_id}', dob='{screening_dob}'")
        print(f"[KYC BG]   (source: {'OCR extracted' if ocr_extracted.get('full_name') else 'user entered'})")

        sanctions_result = {
            "screened": False,
            "is_pep": False,
            "is_sanctioned": False,
            "risk_level": "LOW",
            "pep_matches": [],
            "sanctions_matches": [],
            "error": None,
        }

        try:
            from services.sanctions_screening_service import screen_individual

            sanctions_result = screen_individual(
                full_name=screening_name,
                id_number=screening_id,
                date_of_birth=screening_dob,
                nationality="Nepal",
            )
            print(f"[KYC BG] Sanctions screening result: PEP={sanctions_result['is_pep']}, "
                  f"Sanctioned={sanctions_result['is_sanctioned']}, "
                  f"Risk={sanctions_result['risk_level']}, "
                  f"Matches={sanctions_result['total_matches']}")

            # Save screening result to DB immediately
            kyc_data["sanctions_screening"] = sanctions_result
            put_item("kyc", user_id, kyc_data)

        except Exception as sanctions_err:
            print(f"[KYC BG] Sanctions screening failed (non-blocking): {sanctions_err}")
            sanctions_result["error"] = str(sanctions_err)

        print(f"[KYC BG] STEP 1.5 (PEP/CFT) took {_time.time() - _t15:.1f}s")

        # ============================================================
        # STEP 1.6: CIB REGULATORY CREDIT SCREENING
        # ============================================================
        _t16 = _time.time()
        print("[KYC BG] === STEP 1.6: Running CIB Regulatory Credit Screening ===")

        cib_result = {
            "decision": "PASSED_CIB_GATEWAY",
            "risk_tier": "NEW_TO_CREDIT",
            "reason": "Thin-file applicant.",
            "deductible_liability": 0.0,
            "eligible": True,
            "status": "ELIGIBLE",
        }

        try:
            from services.cib_service import run_cib_regulatory_screening

            if screening_id:
                cib_result = run_cib_regulatory_screening(screening_id)
                print(
                    f"[KYC BG] CIB screening result: decision='{cib_result.get('decision')}', "
                    f"risk_tier='{cib_result.get('risk_tier')}', eligible={cib_result.get('eligible')}"
                )

            # Save CIB screening result to DB immediately
            kyc_data["cib_screening"] = cib_result
            put_item("kyc", user_id, kyc_data)

        except Exception as cib_err:
            print(f"[KYC BG] CIB screening failed (non-blocking): {cib_err}")
            cib_result["error"] = str(cib_err)

        print(f"[KYC BG] STEP 1.6 (CIB) took {_time.time() - _t16:.1f}s")

        # ============================================================
        # FINAL: OCR and regulatory results are sent to admin for review.
        # ============================================================
        print("[KYC BG] === Merging all verification results ===")
        ocr_ok = ai_results.get("gov_id_verified", False)
        video_submitted = bool(live_video_ref)

        # PEP/Sanctions flags
        is_pep = sanctions_result.get("is_pep", False)
        is_sanctioned = sanctions_result.get("is_sanctioned", False)
        aml_risk_level = sanctions_result.get("risk_level", "LOW")

        # CIB Credit screening flags
        cib_eligible = cib_result.get("eligible", True)
        cib_decision = cib_result.get("decision", "PASSED_CIB_GATEWAY")

        # If sanctioned or CIB hard-rejected → auto-reject; if PEP → flag for admin review
        if is_sanctioned or cib_decision == "HARD_REJECT" or not cib_eligible:
            ai_suggested_status = "REJECTED"
        elif is_pep:
            ai_suggested_status = "NEEDS_REVIEW"
        else:
            ai_suggested_status = "NEEDS_REVIEW"

        reasons = []
        if not ocr_ok:
            reasons.append("OCR verification failed")
        if not video_submitted:
            reasons.append("Live video was not submitted")
        if is_sanctioned:
            reasons.append("SANCTIONED/CFT: Person found on international sanctions or terrorism financing list")
        if is_pep:
            reasons.append("PEP: Person identified as Politically Exposed Person — requires enhanced due diligence")
        if cib_decision == "HARD_REJECT" or not cib_eligible:
            reasons.append(f"CIB BLACKLIST / DELINQUENCY: {cib_result.get('reason')}")

        final_kyc_result = {
            **ai_results,
            "video_submitted": video_submitted,
            "ai_suggested_status": ai_suggested_status,
            "reason": "; ".join(reasons) or "OCR and live video submitted for admin review.",
            # PEP / AML / CFT screening results
            "pep_screened": sanctions_result.get("screened", False),
            "is_pep": is_pep,
            "is_sanctioned": is_sanctioned,
            "aml_risk_level": aml_risk_level,
            "pep_matches": sanctions_result.get("pep_matches", []),
            "sanctions_matches": sanctions_result.get("sanctions_matches", []),
            "screening_error": sanctions_result.get("error"),
            # CIB Screening results
            "cib_eligible": cib_eligible,
            "cib_decision": cib_decision,
            "cib_risk_tier": cib_result.get("risk_tier"),
            "cib_deductible_liability": cib_result.get("deductible_liability", 0.0),
            "cib_reason": cib_result.get("reason"),
        }

        print(f"[KYC BG] Final result: OCR={ocr_ok}, Video={video_submitted}, PEP={is_pep}, Sanctioned={is_sanctioned}, CIB Eligible={cib_eligible}")
        print(f"[KYC BG] AML Risk Level: {aml_risk_level}")
        print(f"[KYC BG] AI suggested status: {ai_suggested_status}")

        # ---- UPDATE DB STATE ----
        kyc_data = get_item("kyc", user_id)  # Re-read in case of concurrent changes
        kyc_data["final_result"] = final_kyc_result
        kyc_data["stage"] = STAGE_DONE
        kyc_data["status"] = "PENDING_ADMIN_REVIEW"
        put_item("kyc", user_id, kyc_data)

        print(f"[KYC BG] Background verification COMPLETE for {user_id}")
        print(f"[KYC BG] TOTAL TIME: {_time.time() - _t_total:.1f}s")

    except Exception as e:
        print(f"[KYC BG] CRITICAL ERROR in background verification for {user_id}: {e}")
        import traceback
        traceback.print_exc()
        # Mark as failed so user can retry
        try:
            kyc_data = get_item("kyc", user_id)
            if kyc_data:
                kyc_data["status"] = "PENDING_ADMIN_REVIEW"
                kyc_data["stage"] = STAGE_DONE
                kyc_data["final_result"] = {"error": str(e), "ai_suggested_status": "NEEDS_REVIEW"}
                put_item("kyc", user_id, kyc_data)
        except Exception:
            pass
