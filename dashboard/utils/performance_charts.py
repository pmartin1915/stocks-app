"""
Performance chart generation utilities for portfolio analytics.

Provides Plotly chart builders with consistent theming and responsive design
for historical portfolio performance visualization.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any

from dashboard.theme import get_plotly_theme, get_semantic_color


def create_portfolio_value_chart(snapshots: List[Dict]) -> go.Figure:
    """
    Line chart showing portfolio value over time.

    Args:
        snapshots: List of snapshot dicts with keys: snapshot_date, total_value

    Returns:
        Plotly figure with theme applied
    """
    df = pd.DataFrame(snapshots)

    # Calculate percent change from previous snapshot
    df['pct_change'] = df['total_value'].pct_change() * 100

    blue = get_semantic_color('blue')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['snapshot_date'],
        y=df['total_value'],
        mode='lines+markers',
        name='Portfolio Value',
        line=dict(color=blue, width=3),
        marker=dict(size=6),
        hovertemplate=(
            '<b>%{x|%Y-%m-%d}</b><br>' +
            'Value: $%{y:,.2f}<br>' +
            'Change: %{customdata:.2f}%' +
            '<extra></extra>'
        ),
        customdata=df['pct_change']
    ))

    fig.update_layout(
        title='Portfolio Value Over Time',
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        height=400,
        margin=dict(t=50, l=25, r=25, b=25),
        hovermode='x unified',
        **get_plotly_theme()
    )

    return fig


def create_pnl_attribution_chart(snapshots: List[Dict]) -> go.Figure:
    """
    Line chart showing unrealized vs realized P&L over time.

    Args:
        snapshots: List with keys: snapshot_date, unrealized_pnl, realized_pnl_total

    Returns:
        Plotly figure with separate lines (green=realized, blue=unrealized)
    """
    df = pd.DataFrame(snapshots)

    green = get_semantic_color('green')
    blue = get_semantic_color('blue')

    fig = go.Figure()

    # Realized P&L line
    fig.add_trace(go.Scatter(
        x=df['snapshot_date'],
        y=df['realized_pnl_total'],
        mode='lines+markers',
        name='Realized P&L',
        line=dict(color=green, width=2),
        marker=dict(size=5),
        hovertemplate=(
            '<b>%{x|%Y-%m-%d}</b><br>'
            'Realized: $%{y:,.2f}'
            '<extra></extra>'
        ),
    ))

    # Unrealized P&L line
    fig.add_trace(go.Scatter(
        x=df['snapshot_date'],
        y=df['unrealized_pnl'],
        mode='lines+markers',
        name='Unrealized P&L',
        line=dict(color=blue, width=2),
        marker=dict(size=5),
        hovertemplate=(
            '<b>%{x|%Y-%m-%d}</b><br>'
            'Unrealized: $%{y:,.2f}'
            '<extra></extra>'
        ),
    ))

    fig.update_layout(
        title='P&L Attribution Over Time',
        xaxis_title='Date',
        yaxis_title='P&L ($)',
        height=400,
        margin=dict(t=50, l=25, r=25, b=25),
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        **get_plotly_theme()
    )

    return fig


def create_return_percentage_chart(snapshots: List[Dict]) -> go.Figure:
    """
    Line chart showing cumulative return percentage over time.

    Args:
        snapshots: List with keys: snapshot_date, total_value, total_cost_basis

    Returns:
        Plotly figure showing (total_value - total_cost_basis) / total_cost_basis * 100
    """
    df = pd.DataFrame(snapshots)

    # Calculate return percentage for each snapshot (guard against zero cost basis)
    df['return_pct'] = df.apply(
        lambda r: ((r['total_value'] - r['total_cost_basis']) / r['total_cost_basis'] * 100)
        if r['total_cost_basis'] != 0 else 0.0,
        axis=1
    )
    df['return_dollars'] = df['total_value'] - df['total_cost_basis']

    # Determine line color based on final return
    final_return = df['return_pct'].iloc[-1]
    line_color = get_semantic_color('green') if final_return >= 0 else get_semantic_color('red')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['snapshot_date'],
        y=df['return_pct'],
        mode='lines+markers',
        name='Return %',
        line=dict(color=line_color, width=3),
        marker=dict(size=6),
        hovertemplate=(
            '<b>%{x|%Y-%m-%d}</b><br>' +
            'Return: %{y:.2f}%<br>' +
            'Gain/Loss: $%{customdata:,.2f}' +
            '<extra></extra>'
        ),
        customdata=df['return_dollars']
    ))

    # Add 0% reference line
    gray = get_semantic_color('gray')
    fig.add_hline(
        y=0,
        line_dash='dash',
        line_color=gray,
        annotation_text='Break Even',
        annotation_position='right'
    )

    fig.update_layout(
        title='Cumulative Return Percentage',
        xaxis_title='Date',
        yaxis_title='Return (%)',
        height=400,
        margin=dict(t=50, l=25, r=25, b=25),
        hovermode='x unified',
        **get_plotly_theme()
    )

    return fig


def create_portfolio_health_chart(snapshots: List[Dict]) -> go.Figure:
    """
    Dual-axis chart showing weighted F-Score and Z-Score over time.

    Args:
        snapshots: List with keys: snapshot_date, weighted_fscore, weighted_zscore

    Returns:
        Plotly figure with two y-axes (pattern from 5_Trends.py:82-131)
    """
    df = pd.DataFrame(snapshots)

    # Filter out snapshots with missing scores
    df = df.dropna(subset=['weighted_fscore', 'weighted_zscore'])

    if df.empty:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text='No score data available for selected time range',
            xref='paper',
            yref='paper',
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14)
        )
        fig.update_layout(
            height=400,
            **get_plotly_theme()
        )
        return fig

    blue = get_semantic_color('blue')
    gray = get_semantic_color('gray')
    green = get_semantic_color('green')
    red = get_semantic_color('red')

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # F-Score line (primary y-axis)
    fig.add_trace(
        go.Scatter(
            x=df['snapshot_date'],
            y=df['weighted_fscore'],
            name='F-Score',
            mode='lines+markers',
            line=dict(color=blue, width=3),
            marker=dict(size=8)
        ),
        secondary_y=False
    )

    # Z-Score line (secondary y-axis)
    fig.add_trace(
        go.Scatter(
            x=df['snapshot_date'],
            y=df['weighted_zscore'],
            name='Z-Score',
            mode='lines+markers',
            line=dict(color=gray, width=3),
            marker=dict(size=8)
        ),
        secondary_y=True
    )

    from asymmetric.core.scoring.constants import ZSCORE_MFG_GREY_LOW, ZSCORE_MFG_SAFE

    # Add zone reference lines to Z-Score axis
    fig.add_hline(
        y=ZSCORE_MFG_SAFE,
        line_dash='dash',
        line_color=green,
        annotation_text='Safe Zone',
        secondary_y=True
    )
    fig.add_hline(
        y=ZSCORE_MFG_GREY_LOW,
        line_dash='dash',
        line_color=red,
        annotation_text='Distress Zone',
        secondary_y=True
    )

    fig.update_layout(
        title='Portfolio Health Scores Over Time',
        hovermode='x unified',
        height=400,
        margin=dict(t=50, l=25, r=25, b=25),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        **get_plotly_theme()
    )

    fig.update_xaxes(title_text='Date')
    fig.update_yaxes(title_text='F-Score (0-9)', secondary_y=False, range=[0, 9])
    fig.update_yaxes(title_text='Z-Score', secondary_y=True)

    return fig


def create_position_count_chart(snapshots: List[Dict]) -> go.Figure:
    """
    Bar chart showing number of positions over time.

    Args:
        snapshots: List with keys: snapshot_date, position_count

    Returns:
        Plotly figure with bars showing diversification trend
    """
    df = pd.DataFrame(snapshots)

    blue = get_semantic_color('blue')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['snapshot_date'],
        y=df['position_count'],
        name='Position Count',
        marker_color=blue,
        hovertemplate=(
            '<b>%{x|%Y-%m-%d}</b><br>' +
            'Positions: %{y}' +
            '<extra></extra>'
        )
    ))

    # Add trend line if sufficient data points
    if len(df) >= 5:
        # Trailing moving average (no lookahead bias)
        df['ma'] = df['position_count'].rolling(window=5, center=False).mean()
        gray = get_semantic_color('gray')

        fig.add_trace(go.Scatter(
            x=df['snapshot_date'],
            y=df['ma'],
            name='5-Snapshot Avg',
            mode='lines',
            line=dict(color=gray, width=2, dash='dash'),
            hovertemplate=(
                '<b>%{x|%Y-%m-%d}</b><br>' +
                'Avg: %{y:.1f}' +
                '<extra></extra>'
            )
        ))

    fig.update_layout(
        title='Portfolio Diversification Trend',
        xaxis_title='Date',
        yaxis_title='Number of Positions',
        height=400,
        margin=dict(t=50, l=25, r=25, b=25),
        hovermode='x unified',
        **get_plotly_theme()
    )

    return fig
