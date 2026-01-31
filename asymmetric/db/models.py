"""
SQLModel definitions for Asymmetric database.

Defines the schema for:
- Stock: Company tracking
- StockScore: Calculated financial scores
- ScoreHistory: Historical score records for trend analysis
- Thesis: Investment theses
- Decision: Investment decisions
- ScreeningRun: Screening run history
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from asymmetric.db.alert_models import Alert
    from asymmetric.db.portfolio_models import Holding, Transaction


class Stock(SQLModel, table=True):
    """
    Company tracking table.

    Stores basic company information linked to SEC EDGAR data.
    """

    __tablename__ = "stocks"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True, unique=True, max_length=10)
    cik: str = Field(max_length=10)
    company_name: str = Field(max_length=255)
    sic_code: Optional[str] = Field(default=None, max_length=10)
    sic_description: Optional[str] = Field(default=None, max_length=255)
    exchange: Optional[str] = Field(default=None, max_length=20)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    scores: list["StockScore"] = Relationship(back_populates="stock")
    theses: list["Thesis"] = Relationship(back_populates="stock")
    score_history: list["ScoreHistory"] = Relationship(back_populates="stock")
    transactions: list["Transaction"] = Relationship(back_populates="stock")
    holding: Optional["Holding"] = Relationship(back_populates="stock")
    alerts: list["Alert"] = Relationship(back_populates="stock")


class StockScore(SQLModel, table=True):
    """
    Calculated scores for a stock at a point in time.

    Stores Piotroski F-Score (0-9) and Altman Z-Score with interpretations.
    """

    __tablename__ = "stock_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)

    # Piotroski F-Score (0-9)
    piotroski_score: int = Field(ge=0, le=9)
    piotroski_signals_available: int = Field(default=9, ge=0, le=9)
    piotroski_interpretation: Optional[str] = Field(default=None, max_length=100)

    # Piotroski component scores (for breakdown)
    piotroski_profitability: Optional[int] = Field(default=None, ge=0, le=4)
    piotroski_leverage: Optional[int] = Field(default=None, ge=0, le=3)
    piotroski_efficiency: Optional[int] = Field(default=None, ge=0, le=2)

    # Altman Z-Score
    altman_z_score: float
    altman_zone: str = Field(max_length=20)  # "Safe", "Grey", "Distress"
    altman_interpretation: Optional[str] = Field(default=None, max_length=100)
    altman_formula: str = Field(default="manufacturing", max_length=20)

    # Composite score (optional weighted combination)
    composite_score: Optional[float] = None

    # Data context
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = Field(default=None, max_length=10)  # "FY", "Q1", etc.
    data_source: str = Field(default="bulk_data", max_length=20)  # "bulk_data" or "live_api"

    # Timestamps
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    stock: Optional[Stock] = Relationship(back_populates="scores")


class Thesis(SQLModel, table=True):
    """
    Investment thesis for a stock.

    Stores both human-written and AI-generated theses.
    """

    __tablename__ = "theses"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)

    # Content
    summary: str = Field(max_length=500)  # Short summary (1-2 sentences)
    analysis_text: str  # Full analysis (can be long)
    bull_case: Optional[str] = None
    bear_case: Optional[str] = None
    key_metrics: Optional[str] = None  # JSON string of key metrics to monitor

    # AI metadata (if AI-generated)
    ai_model: Optional[str] = Field(default=None, max_length=50)  # "gemini-2.5-pro"
    ai_cost_usd: Optional[float] = None
    ai_tokens_input: Optional[int] = None
    ai_tokens_output: Optional[int] = None
    cached: bool = Field(default=False)

    # Status tracking
    status: str = Field(default="draft", max_length=20)  # draft, active, archived

    # Conviction tracking
    conviction: Optional[int] = Field(default=None, ge=1, le=5)  # 1-5 scale
    conviction_rationale: Optional[str] = Field(default=None, max_length=200)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    stock: Optional[Stock] = Relationship(back_populates="theses")
    decisions: list["Decision"] = Relationship(back_populates="thesis")


class Decision(SQLModel, table=True):
    """
    Investment decision record.

    Tracks decisions made based on theses.
    """

    __tablename__ = "decisions"

    id: Optional[int] = Field(default=None, primary_key=True)
    thesis_id: int = Field(foreign_key="theses.id", index=True)

    # Decision details
    decision: str = Field(max_length=20)  # "buy", "hold", "sell", "pass"
    rationale: str  # Explanation for the decision
    confidence: Optional[int] = Field(default=None, ge=1, le=5)  # 1-5 scale

    # Optional: Price targets
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

    # Timestamps
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    thesis: Optional[Thesis] = Relationship(back_populates="decisions")


class ScreeningRun(SQLModel, table=True):
    """
    Record of screening runs.

    Stores screening criteria and results for reproducibility.
    """

    __tablename__ = "screening_runs"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Criteria (stored as JSON string)
    criteria_json: str  # {"piotroski_min": 7, "altman_min": 2.99, ...}

    # Results
    result_count: int
    result_tickers: str  # Comma-separated list of tickers

    # Metadata
    data_source: str = Field(default="bulk_data", max_length=20)

    # Timestamps
    run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScoreHistory(SQLModel, table=True):
    """
    Historical score record for trend analysis.

    Automatically populated on every score calculation to track
    F-Score and Z-Score trends over time. One record per stock
    per fiscal period (unique constraint enforced).
    """

    __tablename__ = "score_history"
    __table_args__ = (
        UniqueConstraint("stock_id", "fiscal_year", "fiscal_period", name="uq_score_history_period"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)

    # Fiscal period
    fiscal_year: int = Field(index=True)
    fiscal_period: str = Field(max_length=10)  # FY, Q1, Q2, Q3, Q4

    # Piotroski F-Score (0-9)
    piotroski_score: int = Field(ge=0, le=9)
    piotroski_profitability: Optional[int] = Field(default=None, ge=0, le=4)
    piotroski_leverage: Optional[int] = Field(default=None, ge=0, le=3)
    piotroski_efficiency: Optional[int] = Field(default=None, ge=0, le=2)
    piotroski_interpretation: Optional[str] = Field(default=None, max_length=100)

    # Altman Z-Score
    altman_z_score: float
    altman_zone: str = Field(max_length=20)  # Safe, Grey, Distress
    altman_formula: str = Field(default="manufacturing", max_length=20)

    # Data source tracking
    data_source: str = Field(default="bulk_data", max_length=20)  # bulk_data, live_api

    # Timestamps
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    stock: Optional[Stock] = Relationship(back_populates="score_history")
