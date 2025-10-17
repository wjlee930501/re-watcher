#!/usr/bin/env python3
"""Seed example hospital and contact data for testing."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.storage import Repo, get_db_session
from apps.storage.models import HospitalContact
from apps.common import get_logger

logger = get_logger(__name__)


def seed_example_data():
    """Seed example hospital and contacts."""
    logger.info("Seeding example data...")

    # Create example hospital
    hospital = Repo.create_hospital(
        name="테스트 병원",
        naver_place_url="https://m.place.naver.com/hospital/example"
    )

    logger.info(f"Created hospital: {hospital.id} - {hospital.name}")

    # Create example contacts
    with get_db_session() as session:
        contact1 = HospitalContact(
            hospital_id=hospital.id,
            name="담당자1",
            phone="+821012345678",
            is_active=True,
            priority=1
        )
        contact2 = HospitalContact(
            hospital_id=hospital.id,
            name="담당자2",
            phone="+821098765432",
            is_active=True,
            priority=2
        )

        session.add(contact1)
        session.add(contact2)
        session.commit()

        logger.info(f"Created 2 contacts for hospital: {hospital.id}")

    logger.info("Example data seeded successfully")


if __name__ == "__main__":
    seed_example_data()
