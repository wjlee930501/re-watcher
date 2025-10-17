from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    naver_place_url = Column(Text, nullable=False, unique=True)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="active")  # active, quarantined, disabled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    reviews = relationship("Review", back_populates="hospital")
    contacts = relationship("HospitalContact", back_populates="hospital")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    review_hash = Column(String(64), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    is_receipt = Column(Boolean, default=False)
    created_at_page_text = Column(String(100), nullable=True)
    raw_snapshot_path = Column(Text, nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

    # Phase 2: Sentiment analysis fields
    sentiment_label = Column(Text, nullable=True)  # Positive, Neutral, Negative
    sentiment_score = Column(Float, nullable=True)  # 0~1
    analyzed_at = Column(DateTime(timezone=True), nullable=True)

    hospital = relationship("Hospital", back_populates="reviews")
    flagged = relationship("FlaggedReview", back_populates="review", uselist=False)

    __table_args__ = (
        Index("idx_reviews_hospital_id", "hospital_id"),
        Index("idx_reviews_review_hash", "review_hash"),
        Index("idx_reviews_sentiment_label", "sentiment_label"),
    )


class FlaggedReview(Base):
    __tablename__ = "flagged_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    sentiment_label = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
    flagged_at = Column(DateTime(timezone=True), server_default=func.now())

    review = relationship("Review", back_populates="flagged")
    hospital = relationship("Hospital")
    notifications = relationship("NotificationLog", back_populates="flagged_review")

    __table_args__ = (
        Index("idx_flagged_reviews_hospital_id", "hospital_id"),
        Index("idx_flagged_reviews_flagged_at", "flagged_at"),
    )


class HospitalContact(Base):
    __tablename__ = "hospitals_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(Text, nullable=False)
    phone = Column(Text, nullable=False)  # E.164 format
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # 1-3
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital", back_populates="contacts")

    __table_args__ = (
        Index("idx_contacts_hospital_id", "hospital_id"),
        Index("idx_contacts_is_active", "is_active"),
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    from_flagged_id = Column(UUID(as_uuid=True), ForeignKey("flagged_reviews.id"), nullable=False)
    recipient_phone = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)  # nhn_bizmessage, kakao_bizmessage
    template_code = Column(Text, nullable=False)
    request_id = Column(Text, nullable=True)
    idempotency_key = Column(Text, nullable=False)
    status = Column(Text, default="queued")  # queued, sent, delivered, failed, resend_sms, suppressed
    result_code = Column(Text, nullable=True)
    result_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    hospital = relationship("Hospital")
    review = relationship("Review")
    flagged_review = relationship("FlaggedReview", back_populates="notifications")

    __table_args__ = (
        Index("idx_notif_logs_hospital_id", "hospital_id"),
        Index("idx_notif_logs_status", "status"),
        Index("idx_notif_logs_idempotency_key", "idempotency_key"),
    )


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)  # JSON string
