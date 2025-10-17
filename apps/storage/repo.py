from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_
from apps.storage.models import Hospital, Review, FlaggedReview, HospitalContact, NotificationLog
from apps.storage.db import get_db_session
from apps.common import get_logger

logger = get_logger(__name__)


class Repo:
    @staticmethod
    def create_hospital(name: str, naver_place_url: str) -> Hospital:
        """Create a new hospital."""
        with get_db_session() as session:
            hospital = Hospital(name=name, naver_place_url=naver_place_url)
            session.add(hospital)
            session.flush()
            session.refresh(hospital)
            logger.info(f"Created hospital: {hospital.id} - {name}")
            return hospital

    @staticmethod
    def get_hospital_by_url(url: str) -> Optional[Hospital]:
        """Get hospital by Naver place URL."""
        with get_db_session() as session:
            return session.query(Hospital).filter(Hospital.naver_place_url == url).first()

    @staticmethod
    def get_hospital_by_id(hospital_id: str) -> Optional[Hospital]:
        """Get hospital by ID."""
        with get_db_session() as session:
            return session.query(Hospital).filter(Hospital.id == hospital_id).first()

    @staticmethod
    def update_hospital_crawl_time(hospital_id: str):
        """Update hospital's last crawled timestamp."""
        with get_db_session() as session:
            hospital = session.query(Hospital).filter(Hospital.id == hospital_id).first()
            if hospital:
                hospital.last_crawled_at = datetime.utcnow()
                logger.info(f"Updated crawl time for hospital: {hospital_id}")

    @staticmethod
    def create_review(hospital_id: str, review_hash: str, content: str,
                     rating: Optional[int] = None, is_receipt: bool = False,
                     created_at_page_text: Optional[str] = None,
                     raw_snapshot_path: Optional[str] = None) -> Review:
        """Create a new review."""
        with get_db_session() as session:
            review = Review(
                hospital_id=hospital_id,
                review_hash=review_hash,
                content=content,
                rating=rating,
                is_receipt=is_receipt,
                created_at_page_text=created_at_page_text,
                raw_snapshot_path=raw_snapshot_path
            )
            session.add(review)
            session.flush()
            session.refresh(review)
            logger.info(f"Created review: {review.id} for hospital: {hospital_id}")
            return review

    @staticmethod
    def review_exists(review_hash: str) -> bool:
        """Check if review with given hash exists."""
        with get_db_session() as session:
            # Use exists() for better performance than count()
            from sqlalchemy import exists, select
            return session.query(
                exists(select(Review.id).where(Review.review_hash == review_hash))
            ).scalar()

    @staticmethod
    def fetch_unanalyzed_reviews(limit: int = 200) -> List[Review]:
        """Fetch reviews that haven't been analyzed for sentiment."""
        with get_db_session() as session:
            reviews = session.query(Review).filter(
                Review.sentiment_label.is_(None)
            ).limit(limit).all()
            # Detach from session
            session.expunge_all()
            return reviews

    @staticmethod
    def update_sentiment(review_id: str, label: str, score: float, analyzed_at: datetime):
        """Update review's sentiment analysis results."""
        with get_db_session() as session:
            review = session.query(Review).filter(Review.id == review_id).first()
            if review:
                review.sentiment_label = label
                review.sentiment_score = score
                review.analyzed_at = analyzed_at
                logger.info(f"Updated sentiment for review {review_id}: {label} ({score})")

    @staticmethod
    def flag_review(review: Review):
        """Flag a review as negative and store in flagged_reviews."""
        with get_db_session() as session:
            # Check if already flagged
            existing = session.query(FlaggedReview).filter(
                FlaggedReview.review_id == review.id
            ).first()

            if existing:
                logger.info(f"Review {review.id} already flagged, skipping")
                return

            flagged = FlaggedReview(
                review_id=review.id,
                hospital_id=review.hospital_id,
                content=review.content,
                rating=review.rating,
                sentiment_label=review.sentiment_label,
                sentiment_score=review.sentiment_score,
                collected_at=review.collected_at
            )
            session.add(flagged)
            session.flush()
            logger.info(f"Flagged review: {review.id} for hospital: {review.hospital_id}")

    @staticmethod
    def get_hospital_contacts(hospital_id: str, active_only: bool = True) -> List[HospitalContact]:
        """Get hospital contacts."""
        with get_db_session() as session:
            query = session.query(HospitalContact).filter(
                HospitalContact.hospital_id == hospital_id
            )
            if active_only:
                query = query.filter(HospitalContact.is_active == True)

            contacts = query.order_by(HospitalContact.priority).all()
            session.expunge_all()
            return contacts

    @staticmethod
    def get_new_flagged_reviews(limit: int = 100) -> List[FlaggedReview]:
        """Get new flagged reviews that haven't been notified."""
        with get_db_session() as session:
            # Get flagged reviews without notifications
            subquery = session.query(NotificationLog.from_flagged_id).distinct()

            flagged = session.query(FlaggedReview).filter(
                ~FlaggedReview.id.in_(subquery)
            ).order_by(FlaggedReview.flagged_at).limit(limit).all()

            session.expunge_all()
            return flagged

    @staticmethod
    def create_notification_log(hospital_id: str, review_id: str, from_flagged_id: str,
                               recipient_phone: str, provider: str, template_code: str,
                               idempotency_key: str, request_id: Optional[str] = None,
                               status: str = "queued") -> NotificationLog:
        """Create notification log."""
        with get_db_session() as session:
            log = NotificationLog(
                hospital_id=hospital_id,
                review_id=review_id,
                from_flagged_id=from_flagged_id,
                recipient_phone=recipient_phone,
                provider=provider,
                template_code=template_code,
                request_id=request_id,
                idempotency_key=idempotency_key,
                status=status
            )
            session.add(log)
            session.flush()
            session.refresh(log)
            logger.info(f"Created notification log: {log.id}")
            return log

    @staticmethod
    def update_notification_status(log_id: str, status: str,
                                   result_code: Optional[str] = None,
                                   result_message: Optional[str] = None):
        """Update notification log status."""
        with get_db_session() as session:
            log = session.query(NotificationLog).filter(NotificationLog.id == log_id).first()
            if log:
                log.status = status
                log.result_code = result_code
                log.result_message = result_message
                log.updated_at = datetime.utcnow()
                logger.info(f"Updated notification log {log_id}: {status}")

    @staticmethod
    def check_notification_sent_recently(hospital_id: str, review_id: str,
                                        recipient_phone: str, hours: int = 24) -> bool:
        """Check if notification was sent recently to avoid duplicates."""
        with get_db_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            count = session.query(NotificationLog).filter(
                and_(
                    NotificationLog.hospital_id == hospital_id,
                    NotificationLog.review_id == review_id,
                    NotificationLog.recipient_phone == recipient_phone,
                    NotificationLog.created_at >= cutoff,
                    NotificationLog.status.in_(["sent", "delivered"])
                )
            ).count()
            return count > 0
