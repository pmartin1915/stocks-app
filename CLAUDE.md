# CLAUDE.md — Asymmetric Investment Research Workstation

## Project Overview

Asymmetric is a CLI-first investment research workstation that screens stocks using quantitative criteria (Piotroski F-Score, Altman Z-Score) and conducts AI-powered qualitative analysis via Gemini 2.5. It integrates with Claude Code via MCP for autonomous financial research workflows.

**Owner:** Perry (DNP student, junior developer, value investor)  
**Stack:** Python 3.10+, DuckDB, Gemini 2.5 (Flash + Pro), MCP, Click CLI  
**Data Source:** SEC EDGAR (direct, not third-party APIs)

---

## Critical Constraints (READ FIRST)

### SEC EDGAR Rate Limits
- **HARD LIMIT: 5 requests/second** (not 10 — graylisting risk)
- Always validate response body is non-empty (SEC returns 200 OK with empty body when throttling)
- Use bulk data (`companyfacts.zip`) for historical queries — zero API calls
- User-Agent header REQUIRED: `"Asymmetric/1.0 (email@domain.com)"`

### Gemini 2.5 Pricing Cliffs
- **≤200K tokens:** $1.25/1M input
- **>200K tokens:** $2.50/1M input (DOUBLES!)
- **Context caching is MANDATORY** for multi-query sessions (10x cost reduction)
- Use Flash for bulk ops, Pro only for deep research

### XBRL Parsing
- `edgartools` handles standard US-GAAP tags
- Custom company tags (ARR, NRR, Non-GAAP metrics) get DROPPED by standard parsers
- Use "Raw + Parsed" strategy: standard extraction first, LLM fallback for custom tags

### MCP Transport
- Development: STDIO (simple, ephemeral)
- Production: HTTP (persistent, keeps DuckDB warm)
- Server must support dual-mode via `--transport` flag

---

## Environment Variables

```bash
# Required
SEC_IDENTITY="Asymmetric/1.0 (your-email@domain.com)"
GEMINI_API_KEY="your-gemini-api-key"

# Optional
ANTHROPIC_API_KEY="your-claude-key"  # For optional second-opinion analysis
ASYMMETRIC_DB_PATH="./data/asymmetric.db"
ASYMMETRIC_BULK_DIR="./data/bulk"
ASYMMETRIC_CACHE_DIR="./data/cache"

# MCP Configuration
ENABLE_TOOL_SEARCH=true  # Saves context by enabling efficient tool discovery
```

---

## Project Structure

```
asymmetric/
├── pyproject.toml          # Poetry config — START HERE
├── .env                    # API keys (gitignored)
├── CLAUDE.md               # This file
│
├── cli/                    # Click CLI (primary interface)
│   ├── main.py             # Entry point: asymmetric [command]
│   └── commands/           # lookup, score, screen, analyze, thesis
│
├── core/
│   ├── data/
│   │   ├── rate_limiter.py # Token bucket, 5 req/s, backoff
│   │   ├── edgar_client.py # SEC EDGAR with validation
│   │   └── bulk_manager.py # DuckDB + companyfacts.zip
│   │
│   ├── scoring/
│   │   ├── piotroski.py    # F-Score (9-point)
│   │   ├── altman.py       # Z-Score (bankruptcy risk)
│   │   └── composite.py    # Combined scoring
│   │
│   └── ai/
│       └── gemini_client.py # Context caching, model routing
│
├── mcp/
│   └── server.py           # Dual-mode MCP server
│
├── db/
│   ├── models.py           # SQLModel definitions
│   └── database.py         # Connection management
│
└── data/                   # Local storage (gitignored)
    ├── asymmetric.db       # SQLite for theses/decisions
    ├── sec_data.duckdb     # DuckDB for XBRL bulk data
    └── bulk/               # companyfacts.zip downloads
```

---

## Implementation Order

Build in this sequence to maintain working state at each step:

1. **`pyproject.toml`** — Dependencies (edgartools, duckdb, click, google-generativeai)
2. **`core/data/rate_limiter.py`** — Token bucket with backoff
3. **`core/data/edgar_client.py`** — SEC access with validation
4. **`core/scoring/piotroski.py`** — F-Score calculator
5. **`core/scoring/altman.py`** — Z-Score calculator
6. **`cli/main.py`** — Basic CLI with `lookup` and `score` commands
7. **`core/data/bulk_manager.py`** — DuckDB integration
8. **`core/ai/gemini_client.py`** — Context caching
9. **`mcp/server.py`** — Dual-mode MCP
10. **`db/models.py`** — Thesis/decision persistence

---

## Key Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
edgartools = "^3.0"           # SEC EDGAR access
duckdb = "^1.0"               # OLAP for bulk XBRL data
click = "^8.0"                # CLI framework
rich = "^13.0"                # Terminal formatting
google-generativeai = "^0.8"  # Gemini API
sqlmodel = "^0.0.20"          # SQLite ORM
mcp = "^1.0"                  # MCP SDK
python-dotenv = "^1.0"        # Environment management
httpx = "^0.27"               # Async HTTP client
```

---

## CLI Commands (Target Interface)

```bash
# Company lookup
asymmetric lookup AAPL
asymmetric lookup AAPL --full

# Scoring
asymmetric score AAPL
asymmetric score AAPL --json

# Screening
asymmetric screen --piotroski-min 7 --altman-min 2.99
asymmetric screen --refresh  # Update bulk data first

# AI Analysis
asymmetric analyze AAPL                    # Quick (Flash)
asymmetric analyze AAPL --deep             # Full 10-K (Pro)
asymmetric analyze AAPL --section risks    # Specific section

# Thesis Management
asymmetric thesis create AAPL
asymmetric thesis create AAPL --auto       # AI-generated
asymmetric thesis list
asymmetric thesis view 1

# Database
asymmetric db init
asymmetric db refresh          # Download bulk SEC data
asymmetric db refresh --full   # Full re-download

# MCP Server
asymmetric mcp start                       # STDIO mode
asymmetric mcp start --transport http      # HTTP mode
```

---

## Testing Strategy

```bash
# Unit tests for scoring (known values)
pytest tests/test_scoring.py -v

# Integration test for SEC access (uses live API, rate limited)
pytest tests/test_edgar.py -v --slow

# Test fixtures in tests/fixtures/
# - sample_10k.json (XBRL data)
# - expected_scores.json (known F-Score/Z-Score values)
```

---

## Common Patterns

### Rate-Limited SEC Request
```python
from core.data.rate_limiter import get_limiter

limiter = get_limiter()
limiter.acquire()  # Blocks until token available

response = requests.get(url, headers={"User-Agent": SEC_IDENTITY})

# CRITICAL: Validate response
if not response.content or len(response.content) < 100:
    limiter.report_empty_response()  # Trigger backoff
    raise EmptyResponseError("SEC returned empty body (graylisting)")
```

### Gemini with Context Caching
```python
from core.ai.gemini_client import GeminiClient

client = GeminiClient()

# First call creates cache
result1 = await client.analyze_with_cache(filing_text, "Summarize risks")

# Second call uses cache (10x cheaper)
result2 = await client.analyze_with_cache(filing_text, "Identify moat sources")

print(f"Cached: {result2['cached']}")  # True
print(f"Cost: {result2['estimated_cost']}")  # ~$0.01 vs $0.10
```

### Bulk Data Query (Zero API Calls)
```python
from core.data.bulk_manager import BulkDataManager

bulk = BulkDataManager()

# Query historical data from local DuckDB
revenue_history = bulk.query_financials(
    ticker="AAPL",
    concepts=["Revenues", "NetIncomeLoss"],
    years=5
)
# Zero SEC API calls consumed
```

---

## MCP Tool Naming Convention

Tools follow the pattern: `{action}_{resource}`

- `lookup_company` — Get company metadata
- `get_financials_summary` — Condensed financial data
- `calculate_scores` — Piotroski + Altman
- `get_filing_section` — Lazy-load specific section
- `analyze_filing_with_ai` — Gemini-powered analysis
- `screen_universe` — Filter stocks by criteria
- `extract_custom_metrics` — LLM-aided XBRL parsing

---

## Error Handling

```python
# SEC-specific errors
class SECRateLimitError(Exception): pass
class SECEmptyResponseError(Exception): pass  # Graylisting
class SECIdentityError(Exception): pass       # Missing User-Agent

# Gemini-specific errors
class GeminiContextTooLargeError(Exception): pass  # >200K tokens
class GeminiCacheExpiredError(Exception): pass

# Always wrap SEC calls
try:
    data = edgar.get_financials(ticker)
except SECRateLimitError:
    # Already handled by rate_limiter backoff
    raise
except SECEmptyResponseError:
    logger.warning(f"SEC graylisting detected for {ticker}")
    # Wait and retry, or fall back to bulk data
```

---

## Git Workflow

```bash
# Feature branches
git checkout -b feature/scoring-engine
git checkout -b feature/mcp-server

# Commit messages
feat(scoring): implement Piotroski F-Score calculator
fix(edgar): handle empty response graylisting
docs(readme): add CLI usage examples
```

---

## Quick Reference

| Constraint | Value | Why |
|------------|-------|-----|
| SEC rate limit | 5 req/s | Graylisting risk at 10 |
| Gemini token threshold | 200K | Cost doubles above |
| Cache TTL | 600s (10 min) | Balance cost vs freshness |
| Bulk data refresh | Daily 4AM | SEC updates overnight |
| Max filing size | ~150K tokens | Typical 10-K |

---

## Multi-Model Workflow (Claude + Gemini)

This project uses a multi-model orchestration pattern where Claude acts as the "captain" (orchestrator) and Gemini handles execution of routine tasks.

### Model Selection Strategy

| Model | Use For | Cost Tier |
|-------|---------|-----------|
| `gemini-2.5-flash` | Simple implementation, docs, refactoring | $ (80% of work) |
| `gemini-3-pro-preview` | Complex analysis, code review, debugging | $$$ (15% of work) |
| Consensus (multi-model) | Architecture decisions | $$$$ (5% of work) |
| Claude Opus | Orchestration, quality gates, user communication | N/A |

### MCP PAL Tool Mapping

| Task Type | PAL Tool | Model |
|-----------|----------|-------|
| Simple implementation | `mcp__pal__chat` | gemini-2.5-flash |
| Complex features | `mcp__pal__thinkdeep` | gemini-3-pro-preview |
| Bug investigation | `mcp__pal__debug` | gemini-3-pro-preview |
| Code review | `mcp__pal__codereview` | gemini-3-pro-preview |
| Plan auditing | `mcp__pal__planner` | gemini-3-pro-preview |
| Refactoring | `mcp__pal__refactor` | gemini-2.5-flash |
| Architecture decisions | `mcp__pal__consensus` | pro + flash |
| SEC/Financial logic | `mcp__pal__secaudit` | gemini-3-pro-preview |
| Codebase analysis | `mcp__pal__analyze` | gemini-3-pro-preview |
| Test generation | `mcp__pal__testgen` | gemini-3-pro-preview |
| Code flow tracing | `mcp__pal__tracer` | gemini-3-pro-preview |
| Documentation | `mcp__pal__docgen` | gemini-2.5-flash |
| Pre-commit validation | `mcp__pal__precommit` | gemini-3-pro-preview |
| Session handoff | `mcp__pal__handoff` | gemini-2.5-flash |

### Model Aliases

- `pro` = gemini-3-pro-preview
- `gemini3` = gemini-3-pro-preview
- `flash` = gemini-2.5-flash

### Mandatory Gemini Reviews

**Always** use `mcp__pal__codereview` with gemini-3-pro-preview for:
- Financial calculation logic (F-Score, Z-Score, XBRL parsing)
- SEC EDGAR client changes (rate limiting, response validation)
- API key handling or security-sensitive code

### Continuation IDs

Use `continuation_id` to maintain context across Gemini calls:
```python
# First call returns continuation_id
result1 = mcp__pal__chat(prompt="...", model="flash", ...)
# continuation_id: "abc123..."

# Second call reuses context
result2 = mcp__pal__chat(prompt="...", continuation_id="abc123...", ...)
```

Track active continuation_ids in `docs/current-work.md`.

### Skills & Templates

Located in `.claude/`:
- `skills/delegate-plan.md` — Task routing and delegation workflow
- `skills/local-review.md` — Pre-commit code review checklist
- `skills/check-delegations.md` — Resume previous work
- `skills/session-start.md` — Session initialization
- `templates/DELEGATE_SESSION.md` — Structured delegation template

### Quick Commands

- `/delegate` — Start a delegated task with model routing
- `/local-review` — Review uncommitted changes before commit
- `/check-delegations` — Check for work to resume
- `/start` — Initialize session with connectivity check

---

## Links

- [SEC EDGAR API Docs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [edgartools Documentation](https://edgartools.readthedocs.io/)
- [Gemini API Pricing](https://ai.google.dev/pricing)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Final Technical Spec](./docs/asymmetric-v3-final-spec.md)
