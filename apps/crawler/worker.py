import os
from typing import Optional, List
from datetime import datetime
from apps.crawler.http_client import HTTPClient
from apps.crawler.browser_client import BrowserClient
from apps.crawler.parser import ReviewParser
from apps.crawler.dedupe import generate_review_hash
from apps.storage import Repo
from apps.common import settings, get_logger

logger = get_logger(__name__)


class CrawlerWorker:
    """Main crawler worker that orchestrates HTTP and browser crawling."""

    def __init__(self):
        self.http_client = HTTPClient()
        self.snapshot_dir = settings.snapshot_dir
        self.snapshot_enabled = settings.snapshot_enabled
        if self.snapshot_enabled:
            os.makedirs(self.snapshot_dir, exist_ok=True)

    async def crawl_hospital_reviews(self, hospital_id: str, naver_place_url: str,
                                     is_initial: bool = False) -> dict:
        """
        Crawl reviews for a hospital.

        Args:
            hospital_id: Hospital ID
            naver_place_url: Naver Place URL
            is_initial: If True, fetch only latest 10 reviews

        Returns:
            Dictionary with crawl results
        """
        logger.info(f"Starting crawl for hospital {hospital_id}, initial={is_initial}")

        # Try HTTP first
        html = await self.http_client.fetch(naver_place_url)

        # Fallback to browser if HTTP fails
        if not html:
            logger.info(f"HTTP fetch failed, falling back to browser for hospital {hospital_id}")
            async with BrowserClient() as browser:
                html = await browser.fetch(naver_place_url)

        if not html:
            logger.error(f"Failed to fetch page for hospital {hospital_id}")
            return {
                "success": False,
                "hospital_id": hospital_id,
                "new_count": 0,
                "error": "Failed to fetch page"
            }

        # Parse reviews
        limit = 10 if is_initial else None
        parsed_reviews = ReviewParser.parse_reviews(html, limit=limit)

        if not parsed_reviews:
            logger.warning(f"No reviews parsed for hospital {hospital_id}")
            return {
                "success": True,
                "hospital_id": hospital_id,
                "new_count": 0,
                "error": "No reviews found"
            }

        # Save reviews to database
        new_count = 0
        for review_data in parsed_reviews:
            # Generate hash for deduplication
            review_hash = generate_review_hash(
                review_data["content"],
                review_data.get("rating"),
                review_data.get("date_text")
            )

            # Check if review already exists
            if Repo.review_exists(review_hash):
                logger.info(f"Review already exists (hash: {review_hash[:8]}...), stopping incremental crawl")
                # For incremental crawls, stop when we hit a duplicate
                if not is_initial:
                    break
                continue

            # Save snapshot only if enabled (saves disk space)
            snapshot_path = None
            if self.snapshot_enabled:
                try:
                    snapshot_path = f"{self.snapshot_dir}/review_{review_hash[:16]}.html"
                    with open(snapshot_path, 'w', encoding='utf-8') as f:
                        f.write(review_data.get("raw_html", ""))
                except Exception as e:
                    logger.error(f"Failed to save snapshot: {e}")

            # Create review in database
            try:
                Repo.create_review(
                    hospital_id=hospital_id,
                    review_hash=review_hash,
                    content=review_data["content"],
                    rating=review_data.get("rating"),
                    is_receipt=review_data.get("is_receipt", False),
                    created_at_page_text=review_data.get("date_text"),
                    raw_snapshot_path=snapshot_path
                )
                new_count += 1
            except Exception as e:
                logger.error(f"Failed to save review: {e}")
                continue

        # Update hospital's last crawl time
        Repo.update_hospital_crawl_time(hospital_id)

        logger.info(f"Crawl completed for hospital {hospital_id}: {new_count} new reviews")

        return {
            "success": True,
            "hospital_id": hospital_id,
            "new_count": new_count,
            "total_parsed": len(parsed_reviews)
        }


async def crawl_hospital_task(hospital_id: str, naver_place_url: str, is_initial: bool = False):
    """Task function for Celery."""
    worker = CrawlerWorker()
    result = await worker.crawl_hospital_reviews(hospital_id, naver_place_url, is_initial)
    return result
