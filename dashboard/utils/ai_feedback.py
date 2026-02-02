"""AI feedback storage and retrieval utilities.

Provides functions to record and query user feedback on AI-generated content.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from sqlmodel import Session, select

    from asymmetric.db.database import get_engine
    from asymmetric.db.models import AIFeedback

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


def record_ai_feedback(
    content_hash: str,
    content_type: str,
    ticker: str,
    model: str,
    helpful: bool,
    feedback_text: Optional[str] = None,
    prompt_summary: Optional[str] = None,
) -> bool:
    """Record user feedback on AI content.

    Args:
        content_hash: Unique hash identifying the content.
        content_type: Type of content (analysis, thesis, risk).
        ticker: Stock ticker for context.
        model: Model name used.
        helpful: Whether the content was helpful.
        feedback_text: Optional user comment.
        prompt_summary: First 200 chars of prompt for context.

    Returns:
        True if feedback was recorded, False otherwise.
    """
    if not DB_AVAILABLE:
        return False

    try:
        engine = get_engine()
        with Session(engine) as session:
            # Check if feedback already exists for this content
            existing = session.exec(
                select(AIFeedback).where(AIFeedback.content_hash == content_hash)
            ).first()

            if existing:
                # Update existing feedback
                existing.helpful = helpful
                existing.feedback_text = feedback_text
                existing.feedback_at = datetime.now(timezone.utc)
            else:
                # Create new feedback record
                feedback = AIFeedback(
                    content_hash=content_hash,
                    content_type=content_type,
                    ticker=ticker,
                    model=model,
                    prompt_summary=prompt_summary[:200] if prompt_summary else None,
                    helpful=helpful,
                    feedback_text=feedback_text,
                    feedback_at=datetime.now(timezone.utc),
                )
                session.add(feedback)

            session.commit()
            return True

    except Exception as e:
        logger.warning("Failed to record AI feedback: %s", e)
        return False


def get_feedback_stats(model: Optional[str] = None) -> dict:
    """Get feedback statistics for AI content.

    Args:
        model: Optional model name to filter by.

    Returns:
        Dictionary with feedback statistics.
    """
    if not DB_AVAILABLE:
        return {"error": "Database not available"}

    try:
        engine = get_engine()
        with Session(engine) as session:
            query = select(AIFeedback)
            if model:
                query = query.where(AIFeedback.model == model)

            results = session.exec(query).all()

            total = len(results)
            helpful_count = sum(1 for r in results if r.helpful is True)
            not_helpful_count = sum(1 for r in results if r.helpful is False)
            no_feedback = sum(1 for r in results if r.helpful is None)

            return {
                "total": total,
                "helpful": helpful_count,
                "not_helpful": not_helpful_count,
                "no_feedback": no_feedback,
                "helpful_rate": helpful_count / total if total > 0 else 0,
            }

    except Exception as e:
        return {"error": str(e)}


def get_recent_feedback(limit: int = 20) -> list[dict]:
    """Get recent feedback entries.

    Args:
        limit: Maximum number of entries to return.

    Returns:
        List of feedback dictionaries.
    """
    if not DB_AVAILABLE:
        return []

    try:
        engine = get_engine()
        with Session(engine) as session:
            results = session.exec(
                select(AIFeedback)
                .order_by(AIFeedback.feedback_at.desc())
                .limit(limit)
            ).all()

            return [
                {
                    "content_hash": r.content_hash,
                    "content_type": r.content_type,
                    "ticker": r.ticker,
                    "model": r.model,
                    "helpful": r.helpful,
                    "feedback_text": r.feedback_text,
                    "feedback_at": r.feedback_at.isoformat() if r.feedback_at else None,
                }
                for r in results
            ]

    except Exception as e:
        logger.warning("Failed to retrieve AI feedback: %s", e)
        return []
