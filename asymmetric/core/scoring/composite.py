"""
Composite Scoring Engine.

Combines Piotroski F-Score and Altman Z-Score into a unified ranking system
using a gate-and-rank approach:

1. Gate: Filter stocks that meet minimum Piotroski threshold (default >= 7)
2. Rank: Sort remaining stocks by Altman Z-Score descending

This approach:
- Ensures financial quality via Piotroski (operational health)
- Then ranks by bankruptcy risk via Altman (financial stability)
- Provides both scores for full transparency

Usage:
    scorer = CompositeScorer()

    # Score a single stock
    result = scorer.score(current_period, prior_period)

    # Screen multiple stocks
    rankings = scorer.rank_stocks(stock_data_list, piotroski_min=7)
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from asymmetric.core.scoring.altman import AltmanResult, AltmanScorer
from asymmetric.core.scoring.piotroski import PiotroskiResult, PiotroskiScorer
from asymmetric.core.data.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)


@dataclass
class CompositeResult:
    """
    Combined result from Piotroski and Altman scoring.

    Attributes:
        ticker: Stock ticker symbol
        piotroski: Full Piotroski F-Score result
        altman: Full Altman Z-Score result
        passes_gate: Whether stock meets Piotroski threshold
        composite_rank: Position in ranking (1 = best, None if didn't pass gate)
        gate_threshold: Piotroski threshold used for gating
    """

    ticker: str
    piotroski: PiotroskiResult
    altman: AltmanResult
    passes_gate: bool
    composite_rank: Optional[int] = None
    gate_threshold: int = 7

    @property
    def piotroski_score(self) -> int:
        """Convenience accessor for Piotroski score."""
        return self.piotroski.score

    @property
    def altman_z_score(self) -> float:
        """Convenience accessor for Altman Z-Score."""
        return self.altman.z_score

    @property
    def altman_zone(self) -> str:
        """Convenience accessor for Altman zone."""
        return self.altman.zone

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "passes_gate": self.passes_gate,
            "composite_rank": self.composite_rank,
            "gate_threshold": self.gate_threshold,
            "piotroski": {
                "score": self.piotroski.score,
                "max_score": self.piotroski.max_score,
                "interpretation": self.piotroski.interpretation,
            },
            "altman": {
                "z_score": round(self.altman.z_score, 2),
                "zone": self.altman.zone,
                "interpretation": self.altman.interpretation,
            },
        }


class CompositeScorer:
    """
    Combined scoring engine using Piotroski gate + Altman ranking.

    The gate-and-rank approach:
    1. First, stocks must pass the Piotroski threshold (default >= 7)
    2. Then, passing stocks are ranked by Altman Z-Score (higher = better)

    This ensures we only consider operationally healthy companies,
    then prioritize by financial stability.

    Usage:
        scorer = CompositeScorer()

        # Score single stock
        result = scorer.score_from_dict(current, prior, "AAPL")

        # Rank multiple stocks
        rankings = scorer.rank_stocks(stocks_data, piotroski_min=7)
    """

    def __init__(self) -> None:
        """Initialize the composite scorer with both scoring engines."""
        self.piotroski_scorer = PiotroskiScorer()
        self.altman_scorer = AltmanScorer()

    def score_from_dict(
        self,
        current: dict[str, Any],
        prior: dict[str, Any],
        ticker: str = "",
        piotroski_min: int = 7,
        is_manufacturing: bool = True,
    ) -> CompositeResult:
        """
        Calculate composite score from dictionary data.

        Args:
            current: Current period financial data
            prior: Prior period financial data (for Piotroski comparison)
            ticker: Stock ticker symbol
            piotroski_min: Minimum Piotroski score to pass gate (default 7)
            is_manufacturing: Whether to use manufacturing Altman formula

        Returns:
            CompositeResult with both scores and gate status

        Raises:
            InsufficientDataError: If required data is missing
        """
        # Calculate Piotroski (requires both periods)
        piotroski_result = self.piotroski_scorer.calculate_from_dict(
            current, prior, require_all_signals=False
        )

        # Calculate Altman (requires all components)
        altman_result = self.altman_scorer.calculate_from_dict(
            current,
            is_manufacturing=is_manufacturing,
            require_all_components=True,
        )

        # Determine if passes gate
        passes_gate = piotroski_result.score >= piotroski_min

        return CompositeResult(
            ticker=ticker,
            piotroski=piotroski_result,
            altman=altman_result,
            passes_gate=passes_gate,
            gate_threshold=piotroski_min,
        )

    def rank_stocks(
        self,
        stocks_data: list[dict[str, Any]],
        piotroski_min: int = 7,
        is_manufacturing: bool = True,
    ) -> list[CompositeResult]:
        """
        Score and rank multiple stocks.

        Args:
            stocks_data: List of dicts with keys:
                - ticker: Stock symbol
                - current: Current period financials
                - prior: Prior period financials (can be empty dict)
            piotroski_min: Minimum Piotroski score to pass gate
            is_manufacturing: Whether to use manufacturing Altman formula

        Returns:
            List of CompositeResult, sorted by:
            1. Stocks that pass gate first
            2. Within passing stocks, sorted by Altman Z-Score descending
            3. Non-passing stocks sorted by Piotroski score descending
        """
        results: list[CompositeResult] = []

        for stock in stocks_data:
            ticker = stock.get("ticker", "")
            current = stock.get("current", {})
            prior = stock.get("prior", {})

            try:
                result = self.score_from_dict(
                    current=current,
                    prior=prior,
                    ticker=ticker,
                    piotroski_min=piotroski_min,
                    is_manufacturing=is_manufacturing,
                )
                results.append(result)
            except InsufficientDataError as e:
                logger.debug("Skipping %s: insufficient data - %s", ticker, e)
                continue
            except ValueError as e:
                logger.warning("Error scoring %s: %s", ticker, e)
                continue

        # Separate passing and non-passing stocks
        passing = [r for r in results if r.passes_gate]
        not_passing = [r for r in results if not r.passes_gate]

        # Sort passing stocks by Altman Z-Score descending (higher = better)
        passing.sort(key=lambda r: r.altman_z_score, reverse=True)

        # Sort non-passing stocks by Piotroski score descending
        not_passing.sort(key=lambda r: r.piotroski_score, reverse=True)

        # Assign ranks to passing stocks
        for i, result in enumerate(passing, start=1):
            result.composite_rank = i

        # Combine: passing first, then non-passing
        return passing + not_passing

    def get_top_stocks(
        self,
        stocks_data: list[dict[str, Any]],
        limit: int = 10,
        piotroski_min: int = 7,
        is_manufacturing: bool = True,
    ) -> list[CompositeResult]:
        """
        Get the top-ranked stocks that pass the gate.

        Convenience method that returns only stocks that:
        1. Pass the Piotroski gate
        2. Have the highest Altman Z-Scores

        Args:
            stocks_data: List of stock data dicts
            limit: Maximum number of results
            piotroski_min: Minimum Piotroski score
            is_manufacturing: Whether to use manufacturing formula

        Returns:
            Top N stocks that pass the gate, ranked by Altman Z-Score
        """
        rankings = self.rank_stocks(
            stocks_data,
            piotroski_min=piotroski_min,
            is_manufacturing=is_manufacturing,
        )

        # Return only stocks that passed the gate, up to limit
        return [r for r in rankings if r.passes_gate][:limit]
