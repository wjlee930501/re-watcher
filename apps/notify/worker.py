from datetime import datetime, time
from typing import List, Dict
from apps.storage import Repo
from apps.storage.models import FlaggedReview
from apps.notify.providers import NHNBizMessageProvider
from apps.notify.dedup import generate_dedup_key, check_duplicate
from apps.common import settings, get_logger

logger = get_logger(__name__)


def is_quiet_hours() -> bool:
    """Check if current time is within quiet hours."""
    now = datetime.utcnow().time()

    # Parse quiet hours
    start_parts = settings.quiet_hours_start.split(":")
    end_parts = settings.quiet_hours_end.split(":")

    quiet_start = time(int(start_parts[0]), int(start_parts[1]))
    quiet_end = time(int(end_parts[0]), int(end_parts[1]))

    # Handle overnight quiet hours (e.g., 22:00 to 08:00)
    if quiet_start > quiet_end:
        return now >= quiet_start or now <= quiet_end
    else:
        return quiet_start <= now <= quiet_end


def normalize_phone_e164(phone: str) -> str:
    """
    Normalize phone number to E.164 format.

    Args:
        phone: Phone number (e.g., 01012345678 or +821012345678)

    Returns:
        str: E.164 formatted phone number
    """
    # Remove all non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())

    # Add country code if not present
    if digits.startswith('010'):
        digits = '82' + digits[1:]  # Replace leading 0 with country code

    # Ensure + prefix
    if not digits.startswith('+'):
        digits = '+' + digits

    return digits


async def send_notification_for_review(flagged_review: FlaggedReview) -> Dict:
    """
    Send notifications for a flagged review.

    Args:
        flagged_review: Flagged review to notify about

    Returns:
        dict: Results summary
    """
    hospital_id = str(flagged_review.hospital_id)
    review_id = str(flagged_review.review_id)
    flagged_id = str(flagged_review.id)

    logger.info(f"Processing notification for flagged review: {flagged_id}")

    # Get hospital contacts
    contacts = Repo.get_hospital_contacts(hospital_id, active_only=True)

    if not contacts:
        logger.warning(f"No active contacts for hospital: {hospital_id}")
        return {"sent": 0, "skipped": 0, "failed": 0}

    # Limit to max 3 contacts
    contacts = contacts[:3]

    # Check if in quiet hours
    if is_quiet_hours():
        logger.info("In quiet hours, notifications suppressed")
        # Create suppressed logs
        for contact in contacts:
            phone_e164 = normalize_phone_e164(contact.phone)
            dedup_key = generate_dedup_key(hospital_id, review_id, phone_e164)

            Repo.create_notification_log(
                hospital_id=hospital_id,
                review_id=review_id,
                from_flagged_id=flagged_id,
                recipient_phone=phone_e164,
                provider=settings.alim_provider,
                template_code=settings.alim_template_code,
                idempotency_key=dedup_key,
                status="suppressed"
            )

        return {"sent": 0, "skipped": len(contacts), "failed": 0}

    # Initialize provider
    if settings.alim_provider == "nhn_bizmessage":
        provider = NHNBizMessageProvider()
    else:
        logger.error(f"Unsupported provider: {settings.alim_provider}")
        return {"sent": 0, "skipped": 0, "failed": len(contacts)}

    # Send to each contact
    sent_count = 0
    skipped_count = 0
    failed_count = 0

    for contact in contacts:
        phone_e164 = normalize_phone_e164(contact.phone)

        # Check for duplicate
        if check_duplicate(hospital_id, review_id, phone_e164, hours=24):
            skipped_count += 1
            continue

        # Generate dedup key
        dedup_key = generate_dedup_key(hospital_id, review_id, phone_e164)

        # Prepare template parameters
        review_snippet = flagged_review.content[:120] + "..." if len(flagged_review.content) > 120 else flagged_review.content

        params = {
            "hospitalName": flagged_review.hospital.name if hasattr(flagged_review, 'hospital') else "병원",
            "reviewSnippet": review_snippet,
            "reviewLink": "https://m.place.naver.com",  # TODO: Extract actual review link
            "howToRespond": "빠른 사과, 원인 확인, 재방문 유도"
        }

        try:
            # Send notification
            result = await provider.send_alimtalk(
                template_code=settings.alim_template_code,
                recipient_phone=phone_e164,
                params=params,
                idempotency_key=dedup_key
            )

            # Create log
            status = "sent" if result.get("success") else "failed"
            request_id = result.get("request_id")
            result_code = result.get("result_code")
            result_message = result.get("result_message")

            Repo.create_notification_log(
                hospital_id=hospital_id,
                review_id=review_id,
                from_flagged_id=flagged_id,
                recipient_phone=phone_e164,
                provider=settings.alim_provider,
                template_code=settings.alim_template_code,
                request_id=request_id,
                idempotency_key=dedup_key,
                status=status
            )

            if result.get("success"):
                sent_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.error(f"Error sending notification to {phone_e164[:4]}***: {e}")
            failed_count += 1

    logger.info(
        f"Notification processing complete for flagged {flagged_id}: "
        f"sent={sent_count}, skipped={skipped_count}, failed={failed_count}"
    )

    return {
        "sent": sent_count,
        "skipped": skipped_count,
        "failed": failed_count
    }


async def run_notification_worker(limit: int = 100) -> Dict:
    """
    Run notification worker to process new flagged reviews.

    Args:
        limit: Maximum number of flagged reviews to process

    Returns:
        dict: Results summary
    """
    logger.info(f"Starting notification worker (limit={limit})")

    # Get new flagged reviews
    flagged_reviews = Repo.get_new_flagged_reviews(limit=limit)

    if not flagged_reviews:
        logger.info("No new flagged reviews to process")
        return {
            "processed": 0,
            "total_sent": 0,
            "total_skipped": 0,
            "total_failed": 0
        }

    logger.info(f"Processing {len(flagged_reviews)} flagged reviews")

    total_sent = 0
    total_skipped = 0
    total_failed = 0

    for flagged in flagged_reviews:
        result = await send_notification_for_review(flagged)
        total_sent += result["sent"]
        total_skipped += result["skipped"]
        total_failed += result["failed"]

    logger.info(
        f"Notification worker complete: processed={len(flagged_reviews)}, "
        f"sent={total_sent}, skipped={total_skipped}, failed={total_failed}"
    )

    return {
        "processed": len(flagged_reviews),
        "total_sent": total_sent,
        "total_skipped": total_skipped,
        "total_failed": total_failed
    }
