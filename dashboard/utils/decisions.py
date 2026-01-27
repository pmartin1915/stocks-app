"""Decision and thesis management utilities for dashboard.

Provides CRUD operations for the Decision and Thesis models,
following the same patterns as watchlist.py and scoring.py.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from sqlmodel import select

from asymmetric.db.database import get_or_create_stock, get_session, init_db
from asymmetric.db.models import Decision, Stock, StockScore, Thesis


def get_decisions(
    action: Optional[str] = None,
    ticker: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Fetch decisions with optional filters.

    Args:
        action: Filter by decision action (buy/hold/sell/pass) or None for all.
        ticker: Filter by stock ticker or None for all.
        limit: Maximum number of results.

    Returns:
        List of decision dicts with stock data for display.
    """
    init_db()

    with get_session() as session:
        # Build query with joins
        query = (
            select(Decision, Thesis, Stock)
            .join(Thesis, Decision.thesis_id == Thesis.id)
            .join(Stock, Thesis.stock_id == Stock.id)
        )

        if action:
            query = query.where(Decision.decision == action)
        if ticker:
            query = query.where(Stock.ticker == ticker.upper())

        query = query.order_by(Decision.decided_at.desc()).limit(limit)

        results = []
        for decision, thesis, stock in session.exec(query):
            results.append({
                "id": decision.id,
                "ticker": stock.ticker,
                "company_name": stock.company_name,
                "action": decision.decision,
                "confidence": decision.confidence,
                "target_price": decision.target_price,
                "stop_loss": decision.stop_loss,
                "rationale": decision.rationale,
                "thesis_id": decision.thesis_id,
                "thesis_summary": thesis.summary[:100] if thesis.summary else "",
                "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
            })
        return results


def get_decision_by_id(decision_id: int) -> Optional[dict[str, Any]]:
    """
    Fetch a single decision with full details.

    Args:
        decision_id: The decision ID.

    Returns:
        Decision dict with thesis and stock data, or None if not found.
    """
    init_db()

    with get_session() as session:
        query = (
            select(Decision, Thesis, Stock)
            .join(Thesis, Decision.thesis_id == Thesis.id)
            .join(Stock, Thesis.stock_id == Stock.id)
            .where(Decision.id == decision_id)
        )

        result = session.exec(query).first()
        if not result:
            return None

        decision, thesis, stock = result
        return {
            "id": decision.id,
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "action": decision.decision,
            "confidence": decision.confidence,
            "target_price": decision.target_price,
            "stop_loss": decision.stop_loss,
            "rationale": decision.rationale,
            "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
            "thesis_id": thesis.id,
            "thesis_summary": thesis.summary,
            "thesis_status": thesis.status,
        }


def create_decision(
    ticker: str,
    action: str,
    thesis_id: Optional[int] = None,
    rationale: str = "",
    confidence: Optional[int] = None,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
) -> int:
    """
    Create a new decision. Creates default thesis if none provided.

    Args:
        ticker: Stock ticker symbol.
        action: Decision action (buy/hold/sell/pass).
        thesis_id: Optional ID of existing thesis to link.
        rationale: Explanation for the decision.
        confidence: Confidence level 1-5.
        target_price: Optional target price.
        stop_loss: Optional stop loss price.

    Returns:
        The created decision ID.

    Raises:
        ValueError: If thesis_id provided but not found.
    """
    init_db()

    with get_session() as session:
        if thesis_id:
            thesis = session.get(Thesis, thesis_id)
            if not thesis:
                raise ValueError(f"Thesis not found: {thesis_id}")
        else:
            # Create quick thesis for this decision
            stock = get_or_create_stock(ticker.upper())
            stock = session.merge(stock)

            thesis = Thesis(
                stock_id=stock.id,
                summary=f"Quick decision for {ticker.upper()}",
                analysis_text=rationale or f"{action.title()} decision",
                status="active",
            )
            session.add(thesis)
            session.flush()
            thesis_id = thesis.id

        decision = Decision(
            thesis_id=thesis_id,
            decision=action,
            rationale=rationale or f"{action.title()} decision for {ticker.upper()}",
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            decided_at=datetime.now(UTC),
        )
        session.add(decision)
        session.flush()
        return decision.id


def get_theses(
    status: Optional[str] = None,
    ticker: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Fetch theses with optional filters.

    Args:
        status: Filter by status (draft/active/archived) or None for all.
        ticker: Filter by stock ticker or None for all.
        limit: Maximum number of results.

    Returns:
        List of thesis dicts with stock data.
    """
    init_db()

    with get_session() as session:
        query = (
            select(Thesis, Stock)
            .join(Stock, Thesis.stock_id == Stock.id)
        )

        if status:
            query = query.where(Thesis.status == status)
        if ticker:
            query = query.where(Stock.ticker == ticker.upper())

        query = query.order_by(Thesis.created_at.desc()).limit(limit)

        results = []
        for thesis, stock in session.exec(query):
            # Count decisions for this thesis
            decision_count = session.exec(
                select(Decision).where(Decision.thesis_id == thesis.id)
            ).all()

            results.append({
                "id": thesis.id,
                "ticker": stock.ticker,
                "company_name": stock.company_name,
                "summary": thesis.summary,
                "status": thesis.status,
                "ai_generated": bool(thesis.ai_model),
                "ai_model": thesis.ai_model,
                "ai_cost_usd": thesis.ai_cost_usd,
                "decision_count": len(decision_count),
                "created_at": thesis.created_at.isoformat() if thesis.created_at else None,
                "updated_at": thesis.updated_at.isoformat() if thesis.updated_at else None,
            })
        return results


def get_thesis_by_id(thesis_id: int) -> Optional[dict[str, Any]]:
    """
    Fetch a single thesis with full details.

    Args:
        thesis_id: The thesis ID.

    Returns:
        Thesis dict with stock data and decisions, or None if not found.
    """
    init_db()

    with get_session() as session:
        query = (
            select(Thesis, Stock)
            .join(Stock, Thesis.stock_id == Stock.id)
            .where(Thesis.id == thesis_id)
        )

        result = session.exec(query).first()
        if not result:
            return None

        thesis, stock = result

        # Get decisions for this thesis
        decisions = session.exec(
            select(Decision).where(Decision.thesis_id == thesis_id)
        ).all()

        return {
            "id": thesis.id,
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "summary": thesis.summary,
            "analysis_text": thesis.analysis_text,
            "bull_case": thesis.bull_case,
            "bear_case": thesis.bear_case,
            "key_metrics": thesis.key_metrics,
            "status": thesis.status,
            "ai_generated": bool(thesis.ai_model),
            "ai_model": thesis.ai_model,
            "ai_cost_usd": thesis.ai_cost_usd,
            "ai_tokens_input": thesis.ai_tokens_input,
            "ai_tokens_output": thesis.ai_tokens_output,
            "cached": thesis.cached,
            "decision_count": len(decisions),
            "decisions": [
                {
                    "id": d.id,
                    "action": d.decision,
                    "confidence": d.confidence,
                    "decided_at": d.decided_at.isoformat() if d.decided_at else None,
                }
                for d in decisions
            ],
            "created_at": thesis.created_at.isoformat() if thesis.created_at else None,
            "updated_at": thesis.updated_at.isoformat() if thesis.updated_at else None,
        }


def create_thesis(
    ticker: str,
    summary: str,
    analysis_text: str = "",
    bull_case: Optional[str] = None,
    bear_case: Optional[str] = None,
    key_metrics: Optional[str] = None,
    status: str = "draft",
    ai_model: Optional[str] = None,
    ai_cost_usd: Optional[float] = None,
    ai_tokens_input: Optional[int] = None,
    ai_tokens_output: Optional[int] = None,
    cached: bool = False,
) -> int:
    """
    Create a new thesis.

    Args:
        ticker: Stock ticker symbol.
        summary: Short summary (max 500 chars).
        analysis_text: Full analysis text.
        bull_case: Bull case argument.
        bear_case: Bear case argument.
        key_metrics: JSON string of key metrics.
        status: Thesis status (draft/active/archived).
        ai_model: Model used if AI-generated.
        ai_cost_usd: Cost in USD if AI-generated.
        ai_tokens_input: Input tokens if AI-generated.
        ai_tokens_output: Output tokens if AI-generated.
        cached: Whether AI response was cached.

    Returns:
        The created thesis ID.
    """
    init_db()

    with get_session() as session:
        stock = get_or_create_stock(ticker.upper())
        stock = session.merge(stock)

        thesis = Thesis(
            stock_id=stock.id,
            summary=summary[:500],
            analysis_text=analysis_text,
            bull_case=bull_case,
            bear_case=bear_case,
            key_metrics=key_metrics,
            status=status,
            ai_model=ai_model,
            ai_cost_usd=ai_cost_usd,
            ai_tokens_input=ai_tokens_input,
            ai_tokens_output=ai_tokens_output,
            cached=cached,
        )
        session.add(thesis)
        session.flush()
        return thesis.id


def update_thesis_status(thesis_id: int, status: str) -> bool:
    """
    Update thesis status.

    Args:
        thesis_id: The thesis ID.
        status: New status (draft/active/archived).

    Returns:
        True if updated, False if not found.
    """
    init_db()

    with get_session() as session:
        thesis = session.get(Thesis, thesis_id)
        if not thesis:
            return False

        thesis.status = status
        thesis.updated_at = datetime.now(UTC)
        return True


def update_thesis(
    thesis_id: int,
    summary: Optional[str] = None,
    analysis_text: Optional[str] = None,
    bull_case: Optional[str] = None,
    bear_case: Optional[str] = None,
    key_metrics: Optional[str] = None,
    status: Optional[str] = None,
) -> bool:
    """
    Update thesis fields.

    Args:
        thesis_id: The thesis ID.
        summary: New summary (max 500 chars).
        analysis_text: New analysis text.
        bull_case: New bull case.
        bear_case: New bear case.
        key_metrics: New key metrics.
        status: New status (draft/active/archived).

    Returns:
        True if updated, False if not found.
    """
    init_db()

    with get_session() as session:
        thesis = session.get(Thesis, thesis_id)
        if not thesis:
            return False

        if summary is not None:
            thesis.summary = summary[:500]
        if analysis_text is not None:
            thesis.analysis_text = analysis_text
        if bull_case is not None:
            thesis.bull_case = bull_case if bull_case else None
        if bear_case is not None:
            thesis.bear_case = bear_case if bear_case else None
        if key_metrics is not None:
            thesis.key_metrics = key_metrics if key_metrics else None
        if status is not None:
            thesis.status = status

        thesis.updated_at = datetime.now(UTC)
        return True


def create_thesis_from_comparison(
    ticker: str,
    comparison_result: dict[str, Any],
) -> int:
    """
    Create thesis from Compare page AI analysis result.

    Args:
        ticker: Stock ticker to create thesis for.
        comparison_result: AI analysis result dict from run_comparison_analysis.

    Returns:
        The created thesis ID.
    """
    content = comparison_result.get("content", "")
    model = comparison_result.get("model", "")
    cost = comparison_result.get("estimated_cost_usd", 0)

    # Extract summary (first paragraph or first 500 chars)
    paragraphs = content.split("\n\n")
    summary = paragraphs[0][:500] if paragraphs else content[:500]

    return create_thesis(
        ticker=ticker,
        summary=summary,
        analysis_text=content,
        status="draft",
        ai_model=model,
        ai_cost_usd=cost,
        ai_tokens_input=comparison_result.get("token_count_input"),
        ai_tokens_output=comparison_result.get("token_count_output"),
        cached=comparison_result.get("cached", False),
    )


def get_theses_for_ticker(ticker: str) -> list[dict[str, Any]]:
    """
    Get all active theses for a specific ticker.

    Useful for populating thesis selection dropdowns.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        List of active thesis dicts for the ticker.
    """
    return get_theses(status="active", ticker=ticker, limit=50)


def get_stock_latest_scores(ticker: str) -> Optional[dict[str, Any]]:
    """
    Get latest scores for a stock from database.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Score dict or None if not found.
    """
    init_db()

    with get_session() as session:
        query = (
            select(StockScore, Stock)
            .join(Stock, StockScore.stock_id == Stock.id)
            .where(Stock.ticker == ticker.upper())
            .order_by(StockScore.calculated_at.desc())
        )

        result = session.exec(query).first()
        if not result:
            return None

        score, stock = result

        return {
            "piotroski": {
                "score": score.piotroski_score,
                "interpretation": score.piotroski_interpretation,
                "profitability": score.piotroski_profitability,
                "leverage": score.piotroski_leverage,
                "efficiency": score.piotroski_efficiency,
            },
            "altman": {
                "z_score": score.altman_z_score,
                "zone": score.altman_zone,
                "interpretation": score.altman_interpretation,
            },
        }
