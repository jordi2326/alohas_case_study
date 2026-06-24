"""Streamlit styling and metric tooltips."""

from data import MAP_METRIC_OPTIONS, METRIC_DEFINITIONS

METRIC_TOOLTIPS = METRIC_DEFINITIONS

KPI_DETAILS = {
    "Period": (
        "Shows the active date filter. **Last week** uses daily charts; **Last month** uses weekly buckets; "
        "**Weekly** uses the last 8 weeks; longer presets use monthly data. "
        "YoY deltas compare the same range one year earlier."
    ),
    "Net sales": (
        "Total net sales across selected channels in the period. "
        "The delta is the % change vs the prior-year period."
    ),
    "Avg return rate": (
        "Weighted return rate: total returned units ÷ total sold units in the period. "
        "Green deltas are below prior year; red deltas are above."
    ),
    "Top channel": (
        "Channel with the highest net sales in the selected period."
    ),
    "Top country": (
        "Country with the highest net sales in the selected period."
    ),
    "Wholesale net sales": (
        "Total wholesale net sales in the selected period and countries. "
        "The delta is the % change vs the prior-year period."
    ),
    "Wholesale return rate": (
        "Weighted wholesale return rate across the period. "
        "Green deltas are below prior year; red deltas are above."
    ),
    "Wholesale margin": (
        "Wholesale contribution margin as a % of net sales. "
        "The delta tracks margin rate vs the prior-year period."
    ),
    "Top wholesale country": (
        "Country with the highest wholesale net sales in the period."
    ),
    "Top wholesale category": (
        "Product category with the highest wholesale net sales in the period."
    ),
}

CHART_GUIDES = {
    "Net sales": "Monthly net sales by channel. Look for growth trends, seasonality, and channel shifts.",
    "Return rate": "Monthly return rate by channel. Lower lines generally indicate healthier unit economics.",
    "Mix %": "Each channel's share of total net sales per month. Shows how the revenue mix evolves.",
    "Margin %": "Monthly contribution margin % by channel. Highlights profitability differences across channels.",
    "Map metric": "Choropleth map by country. Each country keeps a fixed color; the metric value appears on hover and in rankings.",
    "Country bar": "Ranked countries for the map metric in the filtered period.",
    "Country heatmap": "Net sales matrix of country × channel. Spot strong pairings and white spaces.",
    "Channel table": "Monthly detail by channel with mix, margin, and YoY where available.",
    "Country table": "Monthly detail by country and channel for the filtered geography.",
    "Wholesale country bar": "Top wholesale countries ranked by the selected map metric.",
    "Wholesale category bar": "Top product categories within wholesale for the selected period.",
    "Wholesale country × category": "Net sales matrix of country × category for wholesale.",
    "Wholesale category trend": "Monthly wholesale performance trend split by product category.",
    "Wholesale table": "Monthly wholesale detail by country and category.",
    "Data quality": "Summary of source data issues detected in production tables.",
}

CHANNEL_COLORWAY = ["#0d6efd", "#6610f2", "#d63384", "#20c997", "#fd7e14"]
ACCENT = CHANNEL_COLORWAY[0]
ACCENT_2 = CHANNEL_COLORWAY[1]
GOOD = CHANNEL_COLORWAY[3]
WARN = CHANNEL_COLORWAY[4]
BAD = CHANNEL_COLORWAY[2]

CONTINUOUS_COLORSCALE = [
    [0.0, "#f8f9fa"],
    [0.15, "#cfe2ff"],
    [0.4, ACCENT],
    [0.7, ACCENT_2],
    [1.0, "#4338ca"],
]

RATE_COLORSCALE = [
    [0.0, GOOD],
    [0.35, GOOD],
    [0.55, WARN],
    [0.75, BAD],
    [1.0, BAD],
]

MIX_COLORSCALE = [
    [0.0, "#f8f9fa"],
    [0.2, "#ede9fe"],
    [0.5, "#a78bfa"],
    [1.0, ACCENT_2],
]


def channel_color_map(channels) -> dict[str, str]:
    ordered = sorted(set(channels))
    return {
        channel: CHANNEL_COLORWAY[index % len(CHANNEL_COLORWAY)]
        for index, channel in enumerate(ordered)
    }


COUNTRY_COLORWAY = [
    "#0d6efd",
    "#6610f2",
    "#d63384",
    "#20c997",
    "#fd7e14",
    "#6f42c1",
    "#198754",
    "#dc3545",
]


def country_color_map(countries) -> dict[str, str]:
    ordered = sorted(set(countries))
    return {
        country: COUNTRY_COLORWAY[index % len(COUNTRY_COLORWAY)]
        for index, country in enumerate(ordered)
    }


def category_color_map(categories) -> dict[str, str]:
    ordered = sorted(set(categories))
    return {
        category: COUNTRY_COLORWAY[index % len(COUNTRY_COLORWAY)]
        for index, category in enumerate(ordered)
    }


TABLE_EMBED_CSS = """
body {
  margin: 0;
  padding: 0;
  font-family: Inter, system-ui, sans-serif;
  background: #fff;
  color: #334155;
}
.data-table-scroll {
  max-height: 420px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}
.data-table-scroll table.data-table,
.data-table-scroll table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0;
}
.data-table-scroll thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background-color: #f8fafc !important;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 11px 14px;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
  box-shadow: inset 0 -2px 0 #e2e8f0;
}
.data-table-scroll.dq-table thead th {
  white-space: normal;
  line-height: 1.25;
}
.data-table-scroll tbody td {
  padding: 10px 14px;
  font-size: 0.84rem;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}
.data-table-scroll tbody tr:last-child td {
  border-bottom: none;
}
.data-table-scroll tbody tr:hover td {
  filter: brightness(0.97);
}
.data-table-scroll td:first-child,
.data-table-scroll th:first-child {
  padding-left: 16px;
}
.data-table-scroll td:last-child,
.data-table-scroll th:last-child {
  padding-right: 16px;
}
"""

DQ_INLINE_TABLE_CSS = """
.dq-inline-table {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  margin-top: 0.25rem;
}
.dq-inline-table table.data-table,
.dq-inline-table table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0;
}
.dq-inline-table thead th {
  background-color: #f8fafc !important;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 15px 18px;
  border-bottom: 2px solid #e2e8f0;
  white-space: normal;
  line-height: 1.35;
}
.dq-inline-table tbody td {
  padding: 15px 18px;
  font-size: 0.96rem;
  line-height: 1.5;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
.dq-inline-table tbody tr:last-child td {
  border-bottom: none;
}
.dq-inline-table tbody tr:hover td {
  filter: brightness(0.97);
}
"""

PLOTLY_LAYOUT = {
    "font": {"family": "Inter, system-ui, sans-serif", "color": "#334155"},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 16, "r": 16, "t": 48, "b": 16},
    "title": {"font": {"size": 15, "color": "#0f172a"}},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    "colorway": CHANNEL_COLORWAY,
}

STREAMLIT_CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] {{ font-family: 'Inter', system-ui, sans-serif; }}
  .stApp {{ background: #f8f9fa; }}
  .block-container {{ padding-top: 1.5rem; max-width: 1320px; }}
  div[data-testid="stSidebar"] {{ background: #fff; border-right: 1px solid #dee2e6; }}
  .dashboard-header {{
    background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT_2} 100%);
    color: white; border-radius: 1rem; padding: 1.5rem 1.75rem;
    margin-bottom: 1rem; box-shadow: 0 .5rem 1rem rgba(13, 110, 253, .15);
  }}
  .dashboard-header h1 {{ margin: 0 0 .25rem; font-size: 1.75rem; font-weight: 700; }}
  .dashboard-header p {{ margin: 0; opacity: .9; }}
  div[data-testid="stHorizontalBlock"] {{
    align-items: stretch;
  }}
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
    display: flex;
    flex-direction: column;
  }}
  div[data-testid="stHorizontalBlock"]:has(.kpi-card) > div[data-testid="column"] {{
    flex: 1 1 0 !important;
    min-width: 0;
  }}
  div[data-testid="stHorizontalBlock"]:has(.kpi-card) > div[data-testid="column"] > div {{
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    height: 100%;
  }}
  div[data-testid="column"] > div > div[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) {{
    flex: 1 1 0;
    display: flex;
    flex-direction: column;
    width: 100%;
    min-height: 148px;
    height: 100%;
    background: #fff;
    padding-top: .75rem;
    overflow: visible !important;
  }}
  div[data-testid="column"] > div > div[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) > div {{
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    height: 100%;
  }}
  div[data-testid="column"] > div > div[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) [data-testid="stMarkdown"] {{
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    height: 100%;
  }}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.panel-header),
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) {{
    overflow: visible !important;
  }}
  .kpi-card {{
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    height: 100%;
    min-height: 6.5rem;
  }}
  .kpi-card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .35rem;
    margin-bottom: .35rem;
  }}
  .kpi-card-label {{
    display: block;
    font-size: .82rem;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 0;
  }}
  .panel-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .5rem;
    margin-bottom: .35rem;
  }}
  .panel-header-title {{
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
  }}
  .info-tip {{
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    cursor: help;
  }}
  .info-tip-icon {{
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 999px;
    border: 1px solid #cbd5e1;
    background: #f8fafc;
    color: #64748b;
    font-size: .72rem;
    font-weight: 700;
    line-height: 1.25rem;
    text-align: center;
    display: inline-block;
    user-select: none;
  }}
  .info-tip:hover .info-tip-icon {{
    border-color: {ACCENT};
    color: {ACCENT};
    background: #eff6ff;
  }}
  .info-tip-content {{
    visibility: hidden;
    opacity: 0;
    position: absolute;
    z-index: 1000;
    top: calc(100% + 8px);
    right: 0;
    width: 280px;
    max-width: 80vw;
    padding: .75rem .85rem;
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: .65rem;
    box-shadow: 0 .5rem 1rem rgba(0,0,0,.12);
    font-size: .82rem;
    line-height: 1.45;
    color: #334155;
    text-align: left;
    pointer-events: none;
    transition: opacity .15s ease;
  }}
  .info-tip-content p {{
    margin: 0 0 .45rem;
  }}
  .info-tip-content p:last-child {{
    margin-bottom: 0;
  }}
  .info-tip:hover .info-tip-content {{
    visibility: visible;
    opacity: 1;
  }}
  .kpi-card-value {{
    display: block;
    flex: 1 1 auto;
    font-size: clamp(1.05rem, 1.35vw, 1.45rem);
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
    margin-bottom: .35rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .kpi-card-delta {{
    display: block;
    flex: 0 0 auto;
    font-size: .78rem;
    font-weight: 600;
    line-height: 1.35;
    min-height: 1.35rem;
    margin-top: auto;
    margin-bottom: .15rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .kpi-card-delta-empty {{
    visibility: hidden;
  }}
  .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
    border-bottom-color: {ACCENT} !important;
    color: {ACCENT} !important;
  }}
  .stTabs [data-baseweb="tab-list"] button {{
    color: #64748b !important;
  }}
  div[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background-color: {ACCENT} !important;
  }}
  div[data-testid="stSidebar"] [data-baseweb="tag"] span {{
    color: #fff !important;
  }}
  div[data-testid="stSidebar"] button[kind="primary"] {{
    background-color: {ACCENT} !important;
    border-color: {ACCENT} !important;
    color: #fff !important;
  }}
  div[data-testid="stSidebar"] button[kind="primary"]:hover {{
    background-color: #0b5ed7 !important;
    border-color: #0b5ed7 !important;
    color: #fff !important;
  }}
  div[data-testid="stSidebar"] button[kind="secondary"] {{
    background-color: #fff !important;
    border: 1px solid #cbd5e1 !important;
    color: #475569 !important;
  }}
  div[data-testid="stSidebar"] button[kind="secondary"]:hover {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
    background-color: #eff6ff !important;
  }}
  .insight-footer {{
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid #dee2e6;
  }}
  .insight-footer h4 {{
    margin: 0 0 .75rem;
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
  }}
  #insight-row-marker + div[data-testid="stHorizontalBlock"] {{
    align-items: stretch;
  }}
  #insight-row-marker + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
    display: flex;
    flex-direction: column;
  }}
  .insight-box {{
    border-radius: .85rem;
    padding: .85rem 1rem;
    box-sizing: border-box;
    height: 100%;
    min-height: 148px;
    display: flex;
    flex-direction: column;
  }}
  .insight-box h5 {{
    margin: 0 0 .6rem;
    font-size: .82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .04em;
  }}
  .insight-box ul {{
    margin: 0;
    padding-left: 1.1rem;
    flex: 1 1 auto;
  }}
  .insight-box li {{
    font-size: .84rem;
    line-height: 1.45;
    margin-bottom: .4rem;
  }}
  .insight-box li:last-child {{
    margin-bottom: 0;
  }}
  .insight-positive {{
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
  }}
  .insight-positive h5 {{
    color: #047857;
  }}
  .insight-negative {{
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
  }}
  .insight-negative h5 {{
    color: #b91c1c;
  }}
  .insight-neutral {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #475569;
  }}
  .insight-neutral h5 {{
    color: #64748b;
  }}
  .data-table-meta {{
    margin: .15rem 0 .65rem;
    font-size: .78rem;
    color: #94a3b8;
  }}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.data-table-meta) {{
    overflow: visible !important;
  }}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.data-table-meta) iframe {{
    border: none;
    border-radius: .75rem;
  }}
  {DQ_INLINE_TABLE_CSS}
</style>
"""
