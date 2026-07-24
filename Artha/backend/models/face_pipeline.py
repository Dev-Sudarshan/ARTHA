"""Face Pipeline — Liveness checks & video-based face verification.

Exposes:
    check_liveness_single_image(image_path) -> dict
    check_liveness_video(video_path) -> dict
    verify_faces_from_video(id_image_path, video_path) -> dict

Called by kyc_service.py during Step 3.
Uses video_verification.py for frame extraction and face matching.
"""

from __future__ import annotations

import os
import traceback
from typing import Optional

import cv2
import numpy as np


# ================================================================
# LIVENESS — SINGLE IMAGE
# ================================================================

def check_liveness_single_image(image_path: str) -> dict:
    """Lightweight liveness check on a single selfie image.

    Checks:
        1. Face is present (Haar/DeepFace)
        2. Basic quality (not too blurry, reasonable size)
        3. Color distribution (not a printed photo — simple heuristic)

    Returns:
        dict with:
            liveness_passed: bool
            reason: str
    """
    result = {
        "liveness_passed": False,
        "reason": "Unknown",
    }

    if not os.path.isfile(image_path):
        result["reason"] = f"Image not found: {image_path}"
        return result

    try:
        img = cv2.imread(image_path)
        if img is None:
            result["reason"] = "Cannot read image file"
            return result

        h, w = img.shape[:2]

        # --- Check 1: Face detection ---
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )

        if len(faces) == 0:
            # Try DeepFace for better detection
            try:
                from deepface import DeepFace
                face_objs = DeepFace.extract_faces(
                    img_path=image_path,
                    detector_backend="opencv",
                    enforce_detection=False,
                )
                if not face_objs or face_objs[0].get("confidence", 0) < 0.5:
                    result["reason"] = "No face detected in selfie"
                    return result
            except Exception:
                result["reason"] = "No face detected in selfie"
                return result

        # --- Check 2: Blur detection (Laplacian variance) ---
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 30:
            result["reason"] = f"Image too blurry (variance={laplacian_var:.1f})"
            return result

        # --- Check 3: Minimum resolution ---
        if h < 100 or w < 100:
            result["reason"] = f"Image too small ({w}x{h})"
            return result

        # --- Check 4: Basic color variance (detect printed/screen photos) ---
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sat_mean = hsv[:, :, 1].mean()
        val_std = hsv[:, :, 2].std()

        # Real faces tend to have moderate saturation and value variance
        if sat_mean < 5 and val_std < 10:
            result["reason"] = "Image appears to be grayscale/uniform (possible printed photo)"
            return result

        # All checks passed
        result["liveness_passed"] = True
        result["reason"] = "Liveness checks passed"
        print(f"[LIVENESS] Passed — blur={laplacian_var:.1f}, sat={sat_mean:.1f}, faces={len(faces)}")

    except Exception as e:
        result["reason"] = f"Liveness check error: {str(e)}"
        traceback.print_exc()

    return result


# ================================================================
# LIVENESS — VIDEO
# ================================================================

def check_liveness_video(video_path: str) -> dict:
    """Lightweight liveness check on a video.

    Extracts frames and checks that:
        1. Multiple frames contain a face
        2. There is motion between frames (not a static photo)
        3. Frames are not too blurry

    Returns:
        dict with:
            liveness_passed: bool
            reason: str
    """
    result = {
        "liveness_passed": False,
        "reason": "Video verification model removed",
    }

    if not os.path.isfile(video_path):
        result["reason"] = f"Video not found: {video_path}"
        return result

    return result


# ================================================================
# VIDEO FACE VERIFICATION
# ================================================================

def verify_faces_from_video(
    id_image_path: str,
    video_path: str,
) -> dict:
    """Extract frames from video and match face against ID card photo.

    Uses the video_verification module for frame extraction and ArcFace
    matching.

    Args:
        id_image_path: Path to the citizenship card front (reference face).
        video_path: Path to the user's declaration video.

    Returns:
        dict with:
            face_match: bool
            distance: float
            similarity: float
            matched_frame: str | None
            final_status: "APPROVED" | "REJECTED"
            reason: str | None
    """
    result = {
        "face_match": False,
        "distance": 1.0,
        "similarity": 0.0,
        "matched_frame": None,
        "final_status": "REJECTED",
        "reason": "Video verification model removed",
    }

    if not os.path.isfile(id_image_path):
        result["reason"] = f"ID image not found: {id_image_path}"
        return result

    if not os.path.isfile(video_path):
        result["reason"] = f"Video not found: {video_path}"
        return result

    return result
