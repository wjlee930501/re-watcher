import hashlib
from typing import Optional
from apps.storage import Repo
from apps.common import get_logger

logger = get_logger(__name__)


def generate_dedup_key(hospital_id: str, review_id: str, recipient_phone: str) -> str:
    """
    Generate deduplication key for notification.

    Args:
        hospital_id: Hospital ID
        review_id: Review ID
        recipient_phone: Recipient phone number

    Returns:
        str: SHA256 hash as dedup key
    """
    key_input = f"{hospital_id}|{review_id}|{recipient_phone}"
    return hashlib.sha256(key_input.encode('utf-8')).hexdigest()


def check_duplicate(hospital_id: str, review_id: str, recipient_phone: str,
                    hours: int = 24) -> bool:
    """
    Check if notification was already sent recently.

    Args:
        hospital_id: Hospital ID
        review_id: Review ID
        recipient_phone: Recipient phone number
        hours: Time window in hours

    Returns:
        bool: True if duplicate (already sent), False otherwise
    """
    is_duplicate = Repo.check_notification_sent_recently(
        hospital_id, review_id, recipient_phone, hours
    )

    if is_duplicate:
        logger.info(
            f"Duplicate notification suppressed: "
            f"hospital={hospital_id}, review={review_id}, phone={recipient_phone[:4]}***"
        )

    return is_duplicate
