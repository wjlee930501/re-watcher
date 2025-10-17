import hashlib
from typing import Optional


def normalize_text(text: str) -> str:
    """Normalize text for consistent hashing."""
    # Remove extra whitespace, normalize line breaks
    text = " ".join(text.split())
    return text.strip().lower()


def generate_review_hash(content: str, rating: Optional[int], date_text: Optional[str]) -> str:
    """
    Generate SHA256 hash for review deduplication.
    Hash = SHA256(normalize(content) + rating + date)
    """
    normalized = normalize_text(content)
    hash_input = f"{normalized}|{rating or ''}|{date_text or ''}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
