"""Compatibility stub for loan video verification.

The video verification model has been removed from this build.
This module now simply records that the feature is disabled.
"""


def verify_loan_video_background(loan_id: str):
    """No-op placeholder retained for compatibility."""
    print(f"[BG VERIFICATION] Disabled for loan {loan_id}: video verification model removed")


def trigger_background_verification(loan_id: str):
    """No-op placeholder retained for compatibility."""
    print(f"[TRIGGER] Background verification skipped for loan {loan_id}")
