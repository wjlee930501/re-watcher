import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from datetime import datetime
from typing import List
from apps.storage import Repo
from apps.storage.models import Review
from apps.common import settings, get_logger

logger = get_logger(__name__)

# Model configuration
MODEL_NAME = "jinmang2/koelectra-base-discriminator"
LABELS = ["Negative", "Neutral", "Positive"]

# Global model and tokenizer (loaded once per worker)
tokenizer = None
model = None
device = None


def initialize_model():
    """Initialize model and tokenizer (called once per worker)."""
    global tokenizer, model, device

    if model is not None:
        return

    logger.info(f"Loading sentiment model: {MODEL_NAME}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            cache_dir=settings.transformers_cache
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME,
            cache_dir=settings.transformers_cache
        ).to(device)
        model.eval()

        logger.info("Sentiment model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


def softmax(x):
    """Compute softmax values."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)


def analyze_review(text: str) -> tuple:
    """
    Analyze sentiment of a single review.

    Returns:
        tuple: (label, score) where label is Negative/Neutral/Positive
               and score is the positive probability (0-1)
    """
    if model is None:
        initialize_model()

    try:
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        logits = outputs.logits[0].cpu().numpy()
        probs = softmax(logits)

        # Score is positive probability
        score = float(probs[2])

        # Label is argmax
        label = LABELS[int(np.argmax(probs))]

        return label, score

    except Exception as e:
        logger.error(f"Error analyzing review: {e}")
        raise


def analyze_batch(reviews: List[Review]) -> List[tuple]:
    """
    Analyze multiple reviews in a batch for better performance.

    Returns:
        List of (label, score) tuples
    """
    if model is None:
        initialize_model()

    batch_size = settings.sentiment_batch_size
    results = []

    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]
        texts = [r.content for r in batch]

        try:
            # Batch tokenization
            inputs = tokenizer(
                texts,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            ).to(device)

            with torch.no_grad():
                outputs = model(**inputs)

            logits = outputs.logits.cpu().numpy()

            for logit in logits:
                probs = softmax(logit)
                score = float(probs[2])
                label = LABELS[int(np.argmax(probs))]
                results.append((label, score))

        except Exception as e:
            logger.error(f"Error analyzing batch: {e}")
            # Fallback to individual analysis
            for review in batch:
                try:
                    result = analyze_review(review.content)
                    results.append(result)
                except:
                    results.append(("Neutral", 0.5))  # Default on error

    return results


async def run_sentiment_analysis(limit: int = 200) -> dict:
    """
    Run sentiment analysis on unanalyzed reviews with batch processing.

    Args:
        limit: Maximum number of reviews to process

    Returns:
        dict: Results summary
    """
    logger.info(f"Starting sentiment analysis (limit={limit})")

    # Initialize model if not already loaded
    initialize_model()

    # Fetch unanalyzed reviews
    reviews = Repo.fetch_unanalyzed_reviews(limit=limit)

    if not reviews:
        logger.info("No unanalyzed reviews found")
        return {
            "analyzed": 0,
            "flagged": 0
        }

    logger.info(f"Analyzing {len(reviews)} reviews in batches")

    # Batch analysis for better performance
    batch_results = analyze_batch(reviews)

    analyzed_count = 0
    flagged_count = 0

    for review, (label, score) in zip(reviews, batch_results):
        try:
            # Update review with sentiment data
            Repo.update_sentiment(
                review_id=str(review.id),
                label=label,
                score=score,
                analyzed_at=datetime.utcnow()
            )
            analyzed_count += 1

            # Flag if negative
            if label == "Negative" or score <= 0.35:
                # Update review object for flagging
                review.sentiment_label = label
                review.sentiment_score = score
                Repo.flag_review(review)
                flagged_count += 1

                if flagged_count <= 5:  # Log only first 5 to reduce noise
                    logger.info(
                        f"Flagged negative review: {review.id}, "
                        f"label={label}, score={score:.2f}"
                    )

        except Exception as e:
            logger.error(f"Error processing review {review.id}: {e}")
            continue

    logger.info(
        f"Sentiment analysis complete: {analyzed_count} analyzed, "
        f"{flagged_count} flagged"
    )

    return {
        "analyzed": analyzed_count,
        "flagged": flagged_count
    }
