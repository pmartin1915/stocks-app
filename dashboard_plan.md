# Designing financial dashboards for value investors

Individual value investors need dashboards that surface fundamental quality signals, not trading noise. The most effective financial UIs for this audience follow a clear pattern: **lead with composite quality scores** (Piotroski F-Score, Altman Z-Score), provide one-click access to component breakdowns, and make thesis documentation as frictionless as quick note-taking. For Asymmetric's Streamlit implementation, this means prioritizing wide layouts with 4-column metric rows, using Plotly for interactive charts, implementing session state for watchlist persistence, and clearly distinguishing AI-generated theses with subtle visual badges.

## Information hierarchy should lead with quality scores

Professional platforms like Bloomberg and Koyfin bury granular data behind progressive disclosure, keeping the primary view focused on actionable metrics. For value investors, the above-the-fold hierarchy should follow this priority: **current price with fair value gap**, **composite quality scores** (F-Score 0-9, Z-Score with zone indicator), **key valuation ratios** (P/E, P/B, EV/EBITDA), and a **sparkline showing 52-week price context**.

The Piotroski F-Score works best displayed as a single number with color coding—**8-9 in green** (#16A34A), **4-7 in yellow** (#EAB308), **0-3 in red** (#DC2626)—with an expandable breakdown showing all nine criteria grouped by category (Profitability 4 pts, Leverage 3 pts, Efficiency 2 pts). Each criterion displays as a simple checkmark or X, instantly communicating what's passing. Simply Wall St's snowflake visualization proves that non-professional investors grasp radar charts quickly, making this an effective pattern for multi-dimensional scoring.

The Altman Z-Score demands a horizontal gauge with three clearly marked zones: Safe Zone above **2.99** (green), Gray Zone between **1.81-2.99** (yellow), and Distress Zone below **1.81** (red). A needle indicates the current score, with component breakdown available on drill-down showing the weighted contribution of each ratio (Working Capital/Assets × 1.2, Retained Earnings/Assets × 1.4, EBIT/Assets × 3.3, Market Cap/Liabilities × 0.6, Revenue/Assets × 1.0).

Secondary metrics—ROE, ROIC, free cash flow trends, margin trajectories—belong one click away in an expandable section or second tab. The Finviz approach of displaying all metrics simultaneously creates cognitive overload; Koyfin's progressive disclosure pattern performs better for deep fundamental analysis.

## Layout patterns that work for fundamental analysis

The Bloomberg Terminal's evolved approach—moving from rigid four-panel layouts to fully customizable tabbed workspaces—offers the guiding principle: **widget linking**. Selecting a stock in any component should update all linked widgets through a color-coded grouping system. Koyfin implements this with seven color groups, allowing users to create persistent analytical workspaces where watchlist selection automatically refreshes charts, news feeds, and metric panels.

For a Streamlit implementation, the optimal structure uses a **left sidebar for navigation** (Dashboard, Screener, Watchlists, Analysis, Portfolio) with a **right-collapsible panel for watchlist quick-access**. The main content area should follow a 12-column responsive grid with these breakpoints: full-width on mobile, 4-4-4 column arrangements on desktop for metric cards, and full-width for primary charts and data tables.

A master-detail pattern works best for stock analysis: the watchlist table occupies the left third of the screen (or collapses on mobile), while the detail view shows the selected stock's header, score summary, key metrics, and charts. This mirrors the Koyfin pattern where users spend most time in a two-pane view with list on one side and visualization on the other.

For the screener interface, avoid the Finviz all-filters-visible approach. Instead, implement a query builder pattern: start with a clean interface, let users add filters incrementally via an "Add Filter" button, display each applied filter as a removable chip, and show real-time result counts. Predefined screens for value investors—"High F-Score Bargains," "Safe Dividend Payers," "Turnaround Candidates"—should appear in the sidebar for one-click access.

Grid specifications from industry patterns suggest an 8px base unit, 16-24px gutters, 16-24px card padding, 44×44px minimum touch targets, 12-14px font for data, and 16-18px for headers.

## Data visualization that communicates rather than decorates

The choice of chart type should match the analytical question. **Line charts** excel for time-series trends—F-Score evolution over eight quarters, portfolio performance versus benchmarks, revenue trajectories. **Candlestick charts** belong in trading interfaces but add little value for buy-and-hold value investors; consider simple OHLC bars or just close prices. **Waterfall charts** effectively communicate P&L bridges and net income composition. **Heatmaps** following the Finviz treemap algorithm—box size representing market cap, color intensity showing performance magnitude—provide powerful sector-at-a-glance views.

Sparklines deserve special attention for Asymmetric. These axis-free inline charts communicate trends without consuming screen real estate, perfect for showing F-Score history in watchlist table columns. Implementation should include markers for minimum and maximum values, consistent scaling across comparable securities, and area fills to emphasize magnitude.

For gauge and dial visualizations, semicircular designs with clear threshold zones work best. The Piotroski gauge should span 0-9 with distinct color bands; the Z-Score gauge needs clearly marked 1.81 and 2.99 threshold lines. Bullet charts offer a space-efficient alternative when vertical space is constrained.

The industry-standard color palette for financial applications uses **#22C55E** (green) for gains and positive signals, **#EF4444** (red) for losses and failures, **#F59E0B** (amber) for warnings and neutral zones, **#3B82F6** (blue) for primary data and trust signals, and **#6B7280** (gray) for neutral backgrounds. For colorblind accessibility—affecting approximately 8% of male users—avoid pure red-green combinations. A safe alternative palette uses **#0072B2** (blue) for positive, **#D55E00** (vermillion) for negative, and **#E69F00** (orange) for warnings.

Never rely on color alone. Reinforce with directional arrows (▲ for gains, ▼ for losses), checkmarks versus X marks for pass/fail criteria, and explicit text labels. Minimum contrast ratios should be 4.5:1 for body text and 3:1 for large elements.

## Thesis and decision tracking that builds institutional memory

The most effective investment journals combine structured templates with freeform flexibility. Core required fields should include ticker, date, decision type (Buy/Hold/Sell/Pass), and a thesis summary. Expandable optional sections can capture key catalysts, risk factors, valuation methodology, competitive analysis, and target price with time horizon.

Seeking Alpha's Portfolio Notes pattern—attaching notes directly to holdings with reminder alerts for specific dates or prices—offers a compelling model. Notes should link bidirectionally to securities and display on symbol pages as cards showing creation date, thesis snippet, and any alerts. TraderSync and Tradervue demonstrate that trading journals benefit from strategy tags, conviction scores, and expected outcome fields.

The conviction scale works best as a **5-point system** with qualitative labels: 1 (Speculative), 2 (Watchlist Position), 3 (Moderate Conviction), 4 (High Conviction), 5 (Core Position). This maps naturally to position sizing logic. Display conviction visually as filled circles or stars, and track changes over time to identify patterns in how conviction correlates with outcomes.

Decision workflows should capture the "why" at the moment of decision. When a user selects Buy, prompt for thesis summary before confirming. The decision log should display as a reverse-chronological feed with each entry showing: date, ticker, action taken, conviction level, thesis snippet, and (after position closes) actual outcome versus expected. TraderSync's "What-If" analysis—showing how focusing on high-conviction trades would have affected returns—demonstrates the value of outcome tracking.

Historical review interfaces should enable before/after comparison: what was the thesis, what actually happened, and what lessons emerge. Calendar views showing decision clusters help identify behavioral patterns (overtrading during volatility, conviction drift during drawdowns). Tags enable pattern analysis: "Which sectors show my best hit rate? Which strategies underperform?"

## Streamlit-specific implementation that actually works

Streamlit's layout primitives—`st.columns`, `st.container`, `st.expander`, `st.tabs`—map reasonably well to financial dashboard requirements, but mobile responsiveness presents challenges. Columns automatically stack vertically on narrow screens (under ~640px), and this behavior cannot be disabled natively. The `streamlit-screen-stats` library provides a workaround by detecting viewport width at runtime, allowing conditional rendering of different layouts for mobile versus desktop.

```python
from st_screen_stats import WindowQueryHelper
helper = WindowQueryHelper()
is_mobile = helper.maximum_window_size(max_width=480, key="mobile")["status"]
kpi_columns = 1 if is_mobile else 4
```

For charts, **Plotly** offers the most complete financial charting capability with excellent Streamlit integration. Always use `st.plotly_chart(fig, use_container_width=True)` to enable responsive sizing. For performance-critical real-time data, `streamlit-lightweight-charts` wraps TradingView's charting library, providing candlestick and technical indicator charts that render faster than Plotly for large datasets.

Table components require careful selection. `st.dataframe` handles basic display adequately but lacks advanced filtering. `st.data_editor` adds inline editing capability. For professional-grade tables with sorting, filtering, conditional formatting, and column grouping, **AgGrid** (`st_aggrid`) remains the best option despite occasional community-reported bugs. Configure with `GridOptionsBuilder` to enable sidebar filters and numeric column formatting.

State management for watchlists and portfolios uses `st.session_state`, which persists across pages in multi-page apps but resets on page refresh. Initialize defensively:

```python
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'GOOGL', 'MSFT']
```

Caching is critical for data-heavy financial dashboards. Use `@st.cache_data(ttl=3600)` for market data API calls (preventing rate limits while ensuring freshness), and `@st.cache_resource` for database connections and ML models. Set `max_entries` to prevent memory overflow with large universes.

Multi-page apps should follow the native Streamlit pattern with a `pages/` directory containing numbered, emoji-prefixed files (`1_📊_Portfolio.py`, `2_📈_Watchlist.py`). This generates automatic sidebar navigation. For more control over page ordering and visibility, the `st_pages` component offers programmatic configuration.

## Presenting AI-generated content without undermining trust

Financial platforms increasingly blend AI analysis with human research, and clear differentiation is both a UX requirement and a regulatory necessity. FINRA Rule 2210 applies identically to AI-generated and human communications; the SEC has levied penalties for "AI washing" (misrepresenting AI capabilities); and the EU AI Act (effective August 2026) mandates disclosure for AI content that could be perceived as human-made.

Visual indicators should be subtle but unmistakable. Seeking Alpha's Virtual Analyst Reports use explicit text disclosure: "This report was generated using machine learning and commercial AI Large Language Models." Robinhood's Cortex feature brands AI insights with consistent iconography and clear statements that content is "informational" rather than advisory. Amazon labels review summaries as "AI-generated from the text of customer reviews."

The optimal pattern for Asymmetric combines several elements: a **small "AI" badge** (sparkle icon or chip symbol) in the corner of AI-generated content cards, a **light blue or gray background tint** (#E0F2FE or #F3F4F6) distinguishing AI sections from user notes, and an **expandable disclosure** explaining the AI's limitations and data sources. Avoid alarming colors or language that suggests danger; the goal is informed transparency, not alarm.

For investment theses specifically, implement a layered architecture: AI-generated analysis appears first as a summary card, clearly labeled, followed by a separate section for the user's personal thesis and notes. Enable users to annotate AI content, accept or dismiss AI suggestions, and track where their thesis diverges from AI analysis. The Composer pattern—turning natural language prompts into visualized strategies—demonstrates how AI can accelerate research without replacing human judgment.

Confidence indicators help calibrate trust. Where AI makes predictions (price targets, probability of meeting earnings), display confidence levels as percentages or qualitative ratings. Cite data sources ("Based on last 4 quarters of reported financials"). Timestamp when analysis was generated. Note that AI may not reflect information from after a specific date.

## Putting it together for Asymmetric

The Asymmetric dashboard should open to a **Portfolio Overview** showing aggregate value, performance versus benchmark, conviction-weighted returns, and any alert conditions (F-Score drops, Z-Score zone changes). The screener lives one click away, using a query builder interface with saved screens for common value strategies. Stock detail pages follow a master-detail pattern with F-Score and Z-Score prominently displayed in color-coded gauges, expandable component breakdowns, and integrated thesis creation.

Watchlist management should support multiple lists with drag-and-drop reordering, customizable column views saved as templates, and synchronized selection updating all linked widgets. Decision tracking captures every Buy/Hold/Sell/Pass with mandatory thesis summary and optional conviction level, building a searchable archive that links outcomes to original reasoning.

The AI thesis feature generates initial analysis from financial data, clearly badged and disclaimed, which users can accept, modify, or replace with their own notes. Both versions persist, enabling comparison over time. Mobile views collapse to single-column layouts, prioritize the most critical metrics (price, F-Score, Z-Score, conviction), and use expanders to hide secondary information behind deliberate taps.

Color conventions follow industry standards (green gains, red losses, blue informational) with colorblind-safe alternatives available. Chart implementations use Plotly with container-width responsiveness, sparklines for inline trends, and heatmaps for sector comparison views. Performance optimization relies on aggressive caching with TTL-based expiration and lazy loading for deep historical data.

This design respects value investors' time by surfacing quality signals immediately, supports deep research through progressive disclosure, builds institutional memory through rigorous thesis documentation, and maintains trust through transparent AI presentation—all within Streamlit's capabilities and constraints.