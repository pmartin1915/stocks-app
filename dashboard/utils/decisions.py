"""Decision and thesis management utilities for dashboard.

Provides CRUD operations for the Decision and Thesis models,
following the same patterns as watchlist.py and scoring.py.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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
        try:
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
        except SQLAlchemyError as e:
            raise ValueError(f"Failed to fetch decisions: {e}") from e


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
            stock = get_or_create_stock(session, ticker.upper())

            thesis = Thesis(
                stock_id=stock.id,
                summary=f"Quick decision for {ticker.upper()}",
                analysis_text=rationale or f"{action.title()} decision",
                status="active",
            )
            session.add(thesis)
            try:
                session.flush()
            except (SQLAlchemyError, IntegrityError) as e:
                session.rollback()
                raise ValueError(f"Failed to create thesis: {e}") from e
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
        try:
            session.flush()
        except (SQLAlchemyError, IntegrityError) as e:
            session.rollback()
            raise ValueError(f"Failed to create decision: {e}") from e
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
                "conviction": thesis.conviction,
                "conviction_rationale": thesis.conviction_rationale,
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
            "conviction": thesis.conviction,
            "conviction_rationale": thesis.conviction_rationale,
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
        stock = get_or_create_stock(session, ticker.upper())

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

        try:
            session.commit()
        except (SQLAlchemyError, IntegrityError) as e:
            session.rollback()
            raise ValueError(f"Failed to update thesis status: {e}") from e

        return True


def update_thesis(
    thesis_id: int,
    summary: Optional[str] = None,
    analysis_text: Optional[str] = None,
    bull_case: Optional[str] = None,
    bear_case: Optional[str] = None,
    key_metrics: Optional[str] = None,
    status: Optional[str] = None,
    conviction: Optional[int] = None,
    conviction_rationale: Optional[str] = None,
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
        conviction: Conviction level (1-5).
        conviction_rationale: Rationale for conviction level.

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
        if conviction is not None:
            thesis.conviction = conviction
        if conviction_rationale is not None:
            thesis.conviction_rationale = conviction_rationale

        thesis.updated_at = datetime.now(UTC)

        try:
            session.commit()
        except (SQLAlchemyError, IntegrityError) as e:
            session.rollback()
            raise ValueError(f"Failed to update thesis: {e}") from e

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


# ========== Outcome Tracking Functions ==========


def update_decision_outcome(
    decision_id: int,
    actual_outcome: str,
    actual_price: Optional[float] = None,
    lessons_learned: Optional[str] = None,
    hit: Optional[bool] = None,
) -> bool:
    """
    Update a decision with outcome information.

    Args:
        decision_id: The decision ID to update.
        actual_outcome: Description of what actually happened (e.g., "success", "partial", "failure").
        actual_price: Price at time of outcome review.
        lessons_learned: Reflection notes for future reference.
        hit: True if thesis proved correct, False otherwise.

    Returns:
        True if updated, False if decision not found.
    """
    init_db()

    with get_session() as session:
        decision = session.get(Decision, decision_id)
        if not decision:
            return False

        decision.actual_outcome = actual_outcome
        decision.outcome_date = datetime.now(UTC)
        decision.actual_price = actual_price
        decision.lessons_learned = lessons_learned
        decision.hit = hit

        session.add(decision)
        try:
            session.commit()
        except (SQLAlchemyError, IntegrityError) as e:
            session.rollback()
            raise ValueError(f"Failed to update decision outcome: {e}") from e
        return True


def get_decisions_with_outcomes(
    ticker: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Fetch decisions that have outcome data recorded.

    Args:
        ticker: Optional ticker filter.
        limit: Maximum results.

    Returns:
        List of decision dicts including outcome data.
    """
    init_db()

    with get_session() as session:
        query = (
            select(Decision, Thesis, Stock)
            .join(Thesis, Decision.thesis_id == Thesis.id)
            .join(Stock, Thesis.stock_id == Stock.id)
            .where(Decision.actual_outcome.isnot(None))
        )

        if ticker:
            query = query.where(Stock.ticker == ticker.upper())

        query = query.order_by(Decision.outcome_date.desc()).limit(limit)

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
                "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
                "actual_outcome": decision.actual_outcome,
                "outcome_date": decision.outcome_date.isoformat() if decision.outcome_date else None,
                "actual_price": decision.actual_price,
                "lessons_learned": decision.lessons_learned,
                "hit": decision.hit,
                "thesis_summary": thesis.summary,
            })
        return results


def analyze_by_conviction(decisions_with_outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Analyze hit rate grouped by conviction level.

    Args:
        decisions_with_outcomes: List of decisions with outcome data.

    Returns:
        List of dicts with conviction_level, hit_count, total_count, hit_rate_pct.
    """
    from collections import defaultdict

    # Group by conviction
    conviction_stats = defaultdict(lambda: {"hits": 0, "total": 0})

    for decision in decisions_with_outcomes:
        conviction = decision.get("confidence") or 3  # Default to medium
        hit = decision.get("hit")

        if hit is not None:  # Only count decisions with explicit hit/miss
            conviction_stats[conviction]["total"] += 1
            if hit:
                conviction_stats[conviction]["hits"] += 1

    # Convert to list
    results = []
    for conviction_level in range(1, 6):  # 1-5 scale
        stats = conviction_stats.get(conviction_level, {"hits": 0, "total": 0})
        total = stats["total"]
        hits = stats["hits"]
        hit_rate = (hits / total * 100) if total > 0 else 0

        results.append({
            "conviction_level": conviction_level,
            "hit_count": hits,
            "total_count": total,
            "hit_rate_pct": round(hit_rate, 1),
        })

    return results


def calculate_portfolio_return(
    decisions_with_outcomes: list[dict[str, Any]],
    conviction_min: int = 1,
) -> float:
    """
    Calculate hypothetical portfolio return based on decision outcomes.

    Assumes equal position sizing and uses price change from target to actual.

    Args:
        decisions_with_outcomes: List of decisions with outcome data.
        conviction_min: Minimum conviction level to include (1-5).

    Returns:
        Average return percentage across qualifying decisions.
    """
    returns = []

    for decision in decisions_with_outcomes:
        confidence = decision.get("confidence") or 3
        if confidence < conviction_min:
            continue

        target = decision.get("target_price")
        actual = decision.get("actual_price")

        if target and actual and target > 0:
            # Calculate return percentage
            ret = ((actual - target) / target) * 100
            returns.append(ret)

    if not returns:
        return 0.0

    return sum(returns) / len(returns)
