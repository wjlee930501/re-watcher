from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
from apps.common import get_logger

logger = get_logger(__name__)

# Receipt keywords to detect receipt reviews
RECEIPT_KEYWORDS = [
    "영수증", "네이버페이", "방문인증", "방문 인증",
    "receipt", "naver pay", "visit verification"
]


class ReviewParser:
    """Parse Naver Place reviews from HTML."""

    @staticmethod
    def detect_receipt(review_html: str, content: str) -> bool:
        """Detect if review is a receipt/verification review."""
        # Check content for keywords
        content_lower = content.lower()
        for keyword in RECEIPT_KEYWORDS:
            if keyword.lower() in content_lower:
                return True

        # Check HTML for aria-label, alt text, icon names
        soup = BeautifulSoup(review_html, 'lxml')

        # Check aria-labels
        elements_with_aria = soup.find_all(attrs={"aria-label": True})
        for elem in elements_with_aria:
            aria_label = elem.get("aria-label", "").lower()
            for keyword in RECEIPT_KEYWORDS:
                if keyword.lower() in aria_label:
                    return True

        # Check alt text
        images = soup.find_all("img", alt=True)
        for img in images:
            alt_text = img.get("alt", "").lower()
            for keyword in RECEIPT_KEYWORDS:
                if keyword.lower() in alt_text:
                    return True

        return False

    @staticmethod
    def parse_reviews(html: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Parse reviews from Naver Place HTML.
        Returns list of review dictionaries.
        """
        soup = BeautifulSoup(html, 'lxml')
        reviews = []

        # Try multiple selector patterns for robustness
        review_selectors = [
            "li.pui__X35jYm",  # Common Naver Place review list item
            "div.YeINN",       # Alternative selector
            "div[class*='review']",  # Generic review class
        ]

        review_elements = []
        for selector in review_selectors:
            review_elements = soup.select(selector)
            if review_elements:
                logger.info(f"Found {len(review_elements)} reviews with selector: {selector}")
                break

        if not review_elements:
            logger.warning("No review elements found with any selector")
            return reviews

        for idx, elem in enumerate(review_elements):
            if limit and idx >= limit:
                break

            try:
                review_data = ReviewParser._parse_single_review(elem)
                if review_data:
                    reviews.append(review_data)
            except Exception as e:
                logger.error(f"Error parsing review {idx}: {e}")
                continue

        logger.info(f"Successfully parsed {len(reviews)} reviews")
        return reviews

    @staticmethod
    def _parse_single_review(elem) -> Optional[Dict]:
        """Parse a single review element."""
        # Extract content - try multiple selectors
        content_selectors = [
            "span.zPfVt",
            "div.YEtRQ",
            "div[class*='content']",
            "p[class*='review']"
        ]

        content = None
        for selector in content_selectors:
            content_elem = elem.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True)
                break

        if not content:
            return None

        # Extract rating - try to find star rating
        rating = None
        rating_selectors = [
            "div.PXMot em",
            "span[class*='rating']",
            "div[class*='star']"
        ]

        for selector in rating_selectors:
            rating_elem = elem.select_one(selector)
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                # Extract number from rating text
                match = re.search(r'(\d+)', rating_text)
                if match:
                    rating = int(match.group(1))
                    break

        # Extract date text
        date_text = None
        date_selectors = [
            "span.BB35N",
            "time",
            "span[class*='date']"
        ]

        for selector in date_selectors:
            date_elem = elem.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                break

        # Check if receipt review
        review_html = str(elem)
        is_receipt = ReviewParser.detect_receipt(review_html, content)

        return {
            "content": content,
            "rating": rating,
            "date_text": date_text,
            "is_receipt": is_receipt,
            "raw_html": review_html
        }
