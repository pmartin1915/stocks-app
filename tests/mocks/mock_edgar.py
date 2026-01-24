"""Mock helpers for SEC EDGAR client testing."""

from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import MagicMock


@dataclass
class MockCompany:
    """Mock edgartools Company object."""

    ticker: str = "AAPL"
    cik: str = "0000320193"
    name: str = "Apple Inc."
    sic_code: str = "3571"
    sic_description: str = "Electronic Computers"


@dataclass
class MockFiling:
    """Mock edgartools Filing object."""

    accession_number: str = "0000320193-23-000001"
    form: str = "10-K"
    filing_date: str = "2023-10-27"


def create_mock_company(
    ticker: str = "AAPL",
    cik: str = "0000320193",
    name: str = "Apple Inc.",
    sic_code: str = "3571",
) -> MagicMock:
    """
    Create a mock edgartools Company object.

    Args:
        ticker: Stock ticker symbol
        cik: SEC Central Index Key
        name: Company name
        sic_code: Standard Industrial Classification code

    Returns:
        MagicMock configured as a Company object
    """
    company = MagicMock()
    company.ticker = ticker
    company.cik = cik
    company.name = name
    company.sic_code = sic_code
    company.sic_description = "Electronic Computers"
    return company


def create_mock_financials(
    revenue: float = 383285000000,
    net_income: float = 96995000000,
    total_assets: float = 352583000000,
    current_assets: float = 143566000000,
    current_liabilities: float = 145308000000,
    long_term_debt: float = 95281000000,
    operating_cash_flow: float = 110543000000,
    gross_profit: float = 169148000000,
    shares_outstanding: float = 15550000000,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Create mock financial data dictionary.

    Args:
        revenue: Total revenue
        net_income: Net income
        total_assets: Total assets
        current_assets: Current assets
        current_liabilities: Current liabilities
        long_term_debt: Long-term debt
        operating_cash_flow: Operating cash flow
        gross_profit: Gross profit
        shares_outstanding: Shares outstanding
        **kwargs: Additional fields to include

    Returns:
        Dictionary with financial data
    """
    data = {
        "revenue": revenue,
        "net_income": net_income,
        "total_assets": total_assets,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "long_term_debt": long_term_debt,
        "operating_cash_flow": operating_cash_flow,
        "gross_profit": gross_profit,
        "shares_outstanding": shares_outstanding,
    }
    data.update(kwargs)
    return data


def create_mock_edgar_client(
    company: Optional[MagicMock] = None,
    financials: Optional[dict[str, Any]] = None,
) -> MagicMock:
    """
    Create a fully mocked EdgarClient.

    Args:
        company: Mock company to return from get_company
        financials: Mock financials to return from get_financials

    Returns:
        MagicMock configured as an EdgarClient
    """
    client = MagicMock()
    client.get_company.return_value = company or create_mock_company()
    client.get_financials.return_value = {
        "periods": [financials or create_mock_financials()]
    }
    client.get_filing_text.return_value = "Sample 10-K filing text content..."
    return client
