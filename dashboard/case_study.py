"""Case-study answers for the Alohas recruiting exercise."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data import resolve_period_col
from theme import PLOTLY_LAYOUT, channel_color_map, country_color_map

RETURNS_SCHEMA_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 520" role="img"
     aria-label="Entity-relationship diagram for proposed returns schema">
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#64748b"/>
    </marker>
    <marker id="arrow-dash" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8"/>
    </marker>
  </defs>
  <style>
    .entity { fill:#f8fafc; stroke:#94a3b8; stroke-width:1.2; }
    .title { font:600 12px Helvetica,Arial,sans-serif; fill:#0f172a; }
    .field { font:11px Helvetica,Arial,sans-serif; fill:#334155; }
    .edge-label { font:10px Helvetica,Arial,sans-serif; fill:#64748b; }
    .edge { stroke:#64748b; stroke-width:1.2; fill:none; marker-end:url(#arrow); }
    .edge-dash { stroke:#94a3b8; stroke-width:1.2; fill:none; stroke-dasharray:5 4;
                 marker-end:url(#arrow-dash); }
  </style>

  <!-- dim_product -->
  <rect class="entity" x="20" y="20" width="200" height="118" rx="6"/>
  <text class="title" x="32" y="40">dim_product</text>
  <text class="field" x="32" y="58">sku (PK)</text>
  <text class="field" x="32" y="74">name · category</text>
  <text class="field" x="32" y="90">base_price · cost</text>
  <text class="field" x="32" y="106">valid_from / valid_to</text>

  <!-- dim_shipment -->
  <rect class="entity" x="700" y="20" width="200" height="118" rx="6"/>
  <text class="title" x="712" y="40">dim_shipment</text>
  <text class="field" x="712" y="58">shipment_id (PK)</text>
  <text class="field" x="712" y="74">shipping_method</text>
  <text class="field" x="712" y="90">shipping_cost · country</text>
  <text class="field" x="712" y="106">shipped_at</text>

  <!-- fct_sale_order_line_snapshot -->
  <rect class="entity" x="300" y="170" width="320" height="150" rx="6"/>
  <text class="title" x="312" y="190">fct_sale_order_line_snapshot</text>
  <text class="field" x="312" y="208">sale_line_id (PK) · channel</text>
  <text class="field" x="312" y="224">sku (FK) · shipment_id (FK)</text>
  <text class="field" x="312" y="240">quantity_sold · gross_sale · taxes</text>
  <text class="field" x="312" y="256">net_sales_at_sale · sold_at</text>

  <!-- fct_return_event -->
  <rect class="entity" x="80" y="380" width="260" height="126" rx="6"/>
  <text class="title" x="92" y="400">fct_return_event</text>
  <text class="field" x="92" y="418">return_event_id (PK)</text>
  <text class="field" x="92" y="434">sale_line_id (FK)</text>
  <text class="field" x="92" y="450">quantity_returned_delta</text>
  <text class="field" x="92" y="466">net_sales_delta · returned_at</text>
  <text class="field" x="92" y="482">return_destination (stock, …)</text>

  <!-- edges -->
  <path class="edge" d="M220 95 C270 95, 270 210, 300 230"/>
  <text class="edge-label" x="228" y="150">sku</text>
  <path class="edge" d="M700 95 C650 95, 650 210, 620 230"/>
  <text class="edge-label" x="640" y="150">shipment_id</text>
  <path class="edge" d="M400 320 C320 340, 220 360, 200 380"/>
  <text class="edge-label" x="250" y="345">1:N returns</text>
</svg>
"""


def _render_returns_schema_diagram() -> None:
    st.markdown(
        f'<div style="width:100%;overflow-x:auto">{RETURNS_SCHEMA_SVG}</div>',
        unsafe_allow_html=True,
    )


def _case_study_layout(fig: go.Figure, title: str, height: int = 360) -> go.Figure:
    layout = dict(PLOTLY_LAYOUT)
    layout["title"] = {"text": title, **PLOTLY_LAYOUT.get("title", {})}
    layout["height"] = height
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor="#e2e8f0", zeroline=False)
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
    return fig


def _plotly(fig: go.Figure | None, key: str) -> None:
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=key)


def _mutable_row_timeline_fig() -> go.Figure:
    """How one production row changes over time while created_at stays fixed."""
    snapshots = ["5 Sep\n(sale)", "28 Sep\n(after return 1)", "12 Nov\n(after return 2)", "15 Nov\n(today)"]
    net_sales = [200, 100, 0, 0]
    qty_returned = [0, 1, 2, 2]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=snapshots,
            y=net_sales,
            mode="lines+markers",
            name="net_sales on row",
            line={"color": "#2563eb", "width": 3},
            marker={"size": 10},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=snapshots,
            y=qty_returned,
            mode="lines+markers",
            name="quantity_returned on row",
            line={"color": "#dc2626", "width": 3, "dash": "dot"},
            marker={"size": 10},
        ),
        secondary_y=True,
    )
    fig.add_annotation(
        x=0,
        y=210,
        text="created_at = 5 Sep<br>(never changes)",
        showarrow=True,
        arrowhead=2,
        ax=80,
        ay=-40,
        font={"size": 11, "color": "#0f172a"},
        bgcolor="#f8fafc",
        bordercolor="#94a3b8",
        borderwidth=1,
    )
    fig.update_yaxes(title_text="Net sales (€)", tickprefix="€", secondary_y=False)
    fig.update_yaxes(title_text="Units returned", secondary_y=True, rangemode="tozero")
    return _case_study_layout(
        fig,
        "Today's model: one row rewritten — purchase date fixed, metrics change",
        height=340,
    )


def _return_events_timeline_fig() -> go.Figure:
    """One sale with two returns on different dates — visible only with return events."""
    fig = go.Figure()
    events = [
        ("5 Sep", "Sale · 2 units", "#16a34a", 0),
        ("28 Sep", "Return · 1 unit → stock", "#ea580c", 1),
        ("12 Nov", "Return · 1 unit → stock", "#ea580c", 2),
    ]
    for date, label, color, y in events:
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[y],
                mode="markers+text",
                text=[label],
                textposition="top center",
                marker={"size": 18, "color": color, "symbol": "circle"},
                showlegend=False,
            )
        )
    fig.add_shape(
        type="line",
        x0=0,
        x1=2,
        y0=-0.15,
        y1=-0.15,
        line={"color": "#94a3b8", "width": 2},
    )
    fig.add_annotation(
        x=1,
        y=-0.45,
        text="Production stores only the final totals — no returned_at per event",
        showarrow=False,
        font={"size": 11, "color": "#64748b"},
    )
    fig.update_xaxes(
        tickvals=[e[0] for e in events],
        ticktext=[e[0] for e in events],
        title="Calendar time",
    )
    fig.update_yaxes(visible=False, range=[-0.7, 1.4])
    return _case_study_layout(
        fig,
        "Same sale: two returns 30+ days apart (proposed model keeps each event)",
        height=300,
    )


def _stock_vs_pnl_fig() -> go.Figure:
    """Stock by return month vs P&L restatement on purchase month."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Stock view — when units arrive (returned_at)",
            "P&L view — September purchase month (created_at)",
        ),
        horizontal_spacing=0.12,
    )
    fig.add_trace(
        go.Bar(
            x=["Sep 2024", "Nov 2024"],
            y=[1, 1],
            name="Units to stock",
            marker_color=["#f59e0b", "#f59e0b"],
            text=["+1 unit<br>28 Sep", "+1 unit<br>12 Nov"],
            textposition="outside",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=["As of 30 Sep", "As of today"],
            y=[200, 0],
            name="September net sales",
            marker_color=["#16a34a", "#dc2626"],
            text=["€200", "€0"],
            textposition="outside",
        ),
        row=1,
        col=2,
    )
    fig.update_yaxes(title_text="Units returned to stock", row=1, col=1, rangemode="tozero")
    fig.update_yaxes(title_text="Net sales (€)", tickprefix="€", row=1, col=2, rangemode="tozero")
    fig.update_xaxes(title_text="Return month", row=1, col=1)
    fig.update_xaxes(title_text="September report snapshot", row=1, col=2)
    return _case_study_layout(
        fig,
        "Two timelines: stock moves on return date · revenue restates on purchase month",
        height=380,
    )


def _render_returns_problem_charts() -> None:
    st.markdown("**Current model problem — one mutable row hides the return timeline**")
    _plotly(_mutable_row_timeline_fig(), "q2_mutable_timeline")
    st.caption(
        "Synthetic example: the sale happened on 5 Sep. Later returns overwrite `net_sales` and "
        "`quantity_returned`, while `created_at` never changes. This is why the current table cannot "
        "tell us when stock came back or when revenue was subtracted."
    )


def _render_returned_at_comparison() -> None:
    st.markdown("**Why `returned_at` matters**")
    st.caption(
        "Same sale, same final business result, but the model either loses the return timeline or preserves it."
    )

    without_returned_at = pd.DataFrame(
        [{
            "sale_line_id": "A123",
            "created_at": "2024-09-05",
            "quantity_sold": 2,
            "quantity_returned": 2,
            "net_sales_today": "€0",
            "returned_at": "missing",
        }]
    )
    with_returned_at = pd.DataFrame(
        [
            {
                "return_event_id": "R001",
                "sale_line_id": "A123",
                "returned_at": "2024-09-28",
                "qty_delta": 1,
                "net_sales_delta": "€-100",
                "stock_effect": "+1 in Sep",
                "pnl_effect": "subtracts from Sep sale",
            },
            {
                "return_event_id": "R002",
                "sale_line_id": "A123",
                "returned_at": "2024-11-12",
                "qty_delta": 1,
                "net_sales_delta": "€-100",
                "stock_effect": "+1 in Nov",
                "pnl_effect": "subtracts from Sep sale",
            },
        ]
    )

    left, right = st.columns(2)
    with left:
        st.markdown("##### Without `returned_at` — today's mutable row")
        st.markdown(
            """
You only know the **final state**: 2 units were returned and net sales became €0.
You do **not** know whether the return happened in September, November, or split across both.
            """
        )
        st.dataframe(without_returned_at, use_container_width=True, hide_index=True)
        st.markdown(
            """
**What you cannot answer**
- When did stock come back?
- Was it one return or two partial returns?
- Which month should warehouse operations see the returned units?
- What did September look like before the November return arrived?
            """
        )

    with right:
        st.markdown("##### With `returned_at` — proposed return events")
        st.markdown(
            """
Each return movement is preserved. Finance can still restate the original sale month,
and operations can see **when inventory actually came back**. The return event does not need
SKU or unit price here; it needs the **negative net sales movement** caused by the refund.
            """
        )
        st.dataframe(with_returned_at, use_container_width=True, hide_index=True)
        st.markdown(
            """
**What you can answer**
- September stock increased by 1 unit.
- November stock increased by 1 unit.
- September net sales is reduced by €200 in total (`€-100 + €-100`).
- September P&L is restated by both returns because both link back to the original sale.
- The return behaviour is auditable event by event.
            """
        )

    st.markdown(
        """
**Business point:** `created_at` answers *when the customer bought*. `returned_at` answers
*when the product came back*. `net_sales_delta` answers *how much revenue must be subtracted*.
Without those fields, stock reporting and financial restatement get mixed into one overwritten row.
        """
    )


def _render_returns_process_explanation() -> None:
    st.markdown("**Proposed process — how returns should flow**")
    st.markdown(
        """
The fix is not only adding a date column. The model needs to separate the **original sale** from each
**return event**.

| Step | Table / field | What happens | Business meaning |
| --- | --- | --- | --- |
| 1 | `fct_sale_order_line_snapshot` | Store the original sale once: `sale_line_id`, `sold_at`, `quantity_sold`, `net_sales_at_sale` | September sale is frozen as originally sold |
| 2 | `fct_return_event.returned_at` | Add one row per return movement | Operations know when stock came back |
| 3 | `fct_return_event.quantity_returned_delta` | Store returned units per event | Stock can increase in Sep and Nov separately |
| 4 | `fct_return_event.net_sales_delta` | Store the negative revenue impact, e.g. `€-100` | Net revenue is subtracted from the original sale period |
| 5 | Reporting / metric layer | Roll up snapshot + return events at query time | Dashboards can show current returned qty and current net sales without storing another table |

**Example:** sale A123 sold 2 units in September for €200.  
Return R001 on 28 Sep has `quantity_returned_delta = 1` and `net_sales_delta = €-100`.  
Return R002 on 12 Nov has `quantity_returned_delta = 1` and `net_sales_delta = €-100`.

Result:
- **Stock view:** +1 unit in September, +1 unit in November.
- **P&L view:** September net sales goes from €200 to €0 as returns arrive.
- **Audit view:** we can see both return events instead of only the final overwritten row.
        """
    )


def _with_month_year(df: pd.DataFrame, period_col: str) -> pd.DataFrame:
    out = df.copy()
    out["month_year"] = pd.to_datetime(out[period_col]).dt.strftime("%Y-%m")
    return out


def _agg_revenue_margin(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    agg_map: dict[str, tuple[str, str]] = {
        "net_sales": ("net_sales", "sum"),
        "contribution_margin": ("contribution_margin", "sum"),
    }
    if "product_cost" in df.columns:
        agg_map["product_cost"] = ("product_cost", "sum")
    if "shipping_cost" in df.columns:
        agg_map["shipping_cost"] = ("shipping_cost", "sum")
    if "quantity_sold" in df.columns:
        agg_map["quantity_sold"] = ("quantity_sold", "sum")
    if "quantity_returned" in df.columns:
        agg_map["quantity_returned"] = ("quantity_returned", "sum")

    grouped = df.groupby(group_cols, as_index=False).agg(**agg_map)
    grouped["margin_pct"] = grouped["contribution_margin"] / grouped["net_sales"]
    if "quantity_sold" in grouped.columns and "quantity_returned" in grouped.columns:
        grouped["return_rate"] = grouped["quantity_returned"] / grouped["quantity_sold"]
    return grouped


def _revenue_margin_dual_axis_fig(
    agg: pd.DataFrame,
    x_col: str,
    title: str,
    x_label: str,
) -> go.Figure:
    if x_col == "month_year":
        plot_df = agg.sort_values("month_year")
    else:
        plot_df = agg.sort_values("net_sales", ascending=False)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=plot_df[x_col],
            y=plot_df["net_sales"],
            name="Net sales",
            marker_color="#2563eb",
            opacity=0.85,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df[x_col],
            y=plot_df["margin_pct"],
            name="Margin %",
            mode="lines+markers",
            line={"color": "#16a34a", "width": 3},
            marker={"size": 8},
        ),
        secondary_y=True,
    )
    fig.update_xaxes(title_text=x_label)
    fig.update_yaxes(title_text="Net sales (€)", tickprefix="€", tickformat=".2s", secondary_y=False)
    fig.update_yaxes(title_text="Margin %", tickformat=".0%", secondary_y=True)
    return _case_study_layout(fig, title, height=380)


def _revenue_margin_scatter_fig(
    agg: pd.DataFrame,
    label_col: str,
    title: str,
    color_map: dict[str, str],
) -> go.Figure:
    plot_df = agg.sort_values("net_sales", ascending=False)
    if plot_df.empty:
        return _case_study_layout(go.Figure(), title, height=400)

    revenue_ref = plot_df["net_sales"].median()
    margin_ref = plot_df["contribution_margin"].sum() / plot_df["net_sales"].sum()
    max_sales = plot_df["net_sales"].max()
    min_margin = plot_df["margin_pct"].min()
    max_margin = plot_df["margin_pct"].max()

    fig = px.scatter(
        plot_df,
        x="net_sales",
        y="margin_pct",
        color=label_col,
        text=label_col,
        labels={
            "net_sales": "Net sales (€)",
            "margin_pct": "Margin %",
            label_col: label_col.replace("_", " ").title(),
        },
        color_discrete_map=color_map,
        category_orders={label_col: list(color_map.keys())},
    )
    point_positions = [
        "top center",
        "bottom center",
        "middle right",
        "middle left",
        "top right",
        "bottom left",
        "top left",
        "bottom right",
    ]
    fig.update_traces(
        textposition=[
            point_positions[index % len(point_positions)]
            for index in range(len(plot_df))
        ],
        textfont={"size": 10},
        marker={"size": 13, "opacity": 0.88, "line": {"width": 1, "color": "white"}},
    )
    fig.add_vline(
        x=revenue_ref,
        line_width=1.5,
        line_dash="dash",
        line_color="#94a3b8",
    )
    fig.add_hline(
        y=margin_ref,
        line_width=1.5,
        line_dash="dash",
        line_color="#94a3b8",
    )
    quadrant_labels = [
        (0.02, 0.96, "Low rev / high margin<br><b>Niche profit</b>", "left", "top", "#166534", "rgba(220,252,231,0.72)", "#86efac"),
        (0.98, 0.96, "High rev / high margin<br><b>Scale winners</b>", "right", "top", "#166534", "rgba(220,252,231,0.72)", "#86efac"),
        (0.02, 0.04, "Low rev / low margin<br><b>Low priority</b>", "left", "bottom", "#475569", "rgba(241,245,249,0.78)", "#cbd5e1"),
        (0.98, 0.04, "High rev / low margin<br><b>Margin risk</b>", "right", "bottom", "#991b1b", "rgba(254,226,226,0.72)", "#fca5a5"),
    ]
    for x, y, text, xanchor, yanchor, font_color, bgcolor, bordercolor in quadrant_labels:
        fig.add_annotation(
            x=x,
            y=y,
            xref="paper",
            yref="paper",
            text=text,
            showarrow=False,
            xanchor=xanchor,
            yanchor=yanchor,
            align="left",
            font={"size": 9, "color": font_color},
            bgcolor=bgcolor,
            bordercolor=bordercolor,
            borderwidth=1,
            borderpad=3,
        )
    fig.add_annotation(
        x=revenue_ref,
        y=1.02,
        xref="x",
        yref="paper",
        text="median revenue",
        showarrow=False,
        yanchor="bottom",
        font={"size": 10, "color": "#64748b"},
    )
    fig.add_annotation(
        x=1.01,
        y=margin_ref,
        xref="paper",
        yref="y",
        text="avg margin",
        showarrow=False,
        xanchor="left",
        font={"size": 10, "color": "#64748b"},
    )
    fig.update_xaxes(
        tickprefix="€",
        tickformat=".2s",
        showgrid=True,
        gridcolor="#dbe3ef",
        zeroline=False,
        range=[0, max_sales * 1.12],
    )
    fig.update_yaxes(
        tickformat=".0%",
        showgrid=True,
        gridcolor="#dbe3ef",
        zeroline=False,
        range=[max(0, min_margin - 0.03), min(1, max_margin + 0.04)],
    )
    fig = _case_study_layout(fig, title, height=430)
    fig.update_layout(
        margin={"l": 64, "r": 72, "t": 64, "b": 52},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "title": None,
        },
    )
    return fig


def _faceted_monthly_fig(
    agg: pd.DataFrame,
    facet_col: str,
    metric: str,
    title: str,
    color_map: dict[str, str],
) -> go.Figure:
    facets = sorted(agg[facet_col].dropna().unique())
    wrap = min(3, max(len(facets), 1))
    metric_label = "Net sales (€)" if metric == "net_sales" else "Margin %"
    fig = px.bar(
        agg.sort_values("month_year"),
        x="month_year",
        y=metric,
        facet_col=facet_col,
        facet_col_wrap=wrap,
        color=facet_col,
        title=title,
        labels={"month_year": "Month", metric: metric_label, facet_col: facet_col.replace("_", " ").title()},
        color_discrete_map=color_map,
        category_orders={facet_col: facets},
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    if metric == "net_sales":
        fig.update_yaxes(tickprefix="€", tickformat=".2s")
    else:
        fig.update_yaxes(tickformat=".0%")
    layout = dict(PLOTLY_LAYOUT)
    layout["title"] = {"text": title, **PLOTLY_LAYOUT.get("title", {})}
    layout["height"] = max(320, 220 * ((len(facets) + wrap - 1) // wrap))
    layout["margin"] = {"l": 32, "r": 16, "t": 56, "b": 40}
    layout["showlegend"] = False
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor="#e2e8f0", tickangle=-45, tickfont={"size": 10})
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
    fig.for_each_annotation(lambda a: a.update(font={"size": 12, "color": "#0f172a"}))
    return fig


def _revenue_margin_timelapse_fig(channel_df: pd.DataFrame) -> go.Figure | None:
    if channel_df.empty:
        return None
    period_col = resolve_period_col(channel_df)
    monthly = _agg_revenue_margin(_with_month_year(channel_df, period_col), ["month_year"])
    monthly = monthly.sort_values("month_year")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=monthly["month_year"],
            y=monthly["net_sales"],
            name="Net sales",
            marker_color="#2563eb",
            opacity=0.75,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["month_year"],
            y=monthly["contribution_margin"],
            name="Contribution margin (€)",
            mode="lines+markers",
            line={"color": "#7c3aed", "width": 2},
            marker={"size": 7},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["month_year"],
            y=monthly["margin_pct"],
            name="Margin %",
            mode="lines+markers",
            line={"color": "#16a34a", "width": 3},
            marker={"size": 8},
        ),
        secondary_y=True,
    )
    fig.update_xaxes(title_text="Month-year", tickangle=-45)
    fig.update_yaxes(title_text="Net sales & margin (€)", tickprefix="€", tickformat=".2s", secondary_y=False)
    fig.update_yaxes(title_text="Margin %", tickformat=".0%", secondary_y=True)
    return _case_study_layout(
        fig,
        "Time lapse — sales, margin €, and margin %",
        height=400,
    )


def _margin_pct_timelapse_fig(channel_df: pd.DataFrame) -> go.Figure | None:
    if channel_df.empty or "channel" not in channel_df.columns:
        return None
    period_col = resolve_period_col(channel_df)
    monthly = _agg_revenue_margin(
        _with_month_year(channel_df, period_col),
        ["month_year", "channel"],
    )
    colors = channel_color_map(monthly["channel"].unique())
    fig = px.line(
        monthly.sort_values("month_year"),
        x="month_year",
        y="margin_pct",
        color="channel",
        markers=True,
        labels={"month_year": "Month-year", "margin_pct": "Margin %", "channel": "Channel"},
        color_discrete_map=colors,
        category_orders={"channel": list(colors.keys())},
    )
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(tickformat=".0%")
    return _case_study_layout(
        fig,
        "Time lapse — margin % by channel",
        height=380,
    )


def _cost_stack_by_channel_fig(channel_df: pd.DataFrame) -> go.Figure | None:
    if channel_df.empty or "product_cost" not in channel_df.columns:
        return None
    agg = _agg_revenue_margin(channel_df, ["channel"]).sort_values("net_sales", ascending=False)
    agg = agg.copy()
    agg["product_cost_pct"] = agg["product_cost"] / agg["net_sales"]
    agg["shipping_cost_pct"] = agg["shipping_cost"] / agg["net_sales"]
    agg["margin_pct"] = agg["contribution_margin"] / agg["net_sales"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Product cost %",
        x=agg["channel"],
        y=agg["product_cost_pct"],
        marker_color="#f97316",
        text=agg["product_cost_pct"].map(lambda value: f"{value:.0%}"),
        textposition="inside",
        hovertemplate="<b>%{x}</b><br>Product cost: %{y:.1%}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Allocated shipping %",
        x=agg["channel"],
        y=agg["shipping_cost_pct"],
        marker_color="#0ea5e9",
        text=agg["shipping_cost_pct"].map(lambda value: f"{value:.0%}" if value >= 0.03 else ""),
        textposition="inside",
        hovertemplate="<b>%{x}</b><br>Shipping: %{y:.1%}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Contribution margin %",
        x=agg["channel"],
        y=agg["margin_pct"],
        marker_color="#16a34a",
        text=agg["margin_pct"].map(lambda value: f"{value:.0%}"),
        textposition="inside",
        hovertemplate="<b>%{x}</b><br>Contribution margin: %{y:.1%}<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        hovermode="x unified",
        legend_title_text="For each €1 of net sales",
    )
    fig.update_yaxes(title_text="Share of net sales", tickformat=".0%", range=[0, 1])
    fig.update_xaxes(title_text="Channel")
    return _case_study_layout(
        fig,
        "Unit economics by channel — where each €1 of sales goes",
        height=380,
    )


def _unit_economics_takeaway(channel_df: pd.DataFrame) -> str | None:
    if channel_df.empty or "product_cost" not in channel_df.columns:
        return None
    agg = _agg_revenue_margin(channel_df, ["channel"])
    agg = agg.copy()
    agg["margin_pct"] = agg["contribution_margin"] / agg["net_sales"]
    agg["cost_pct"] = (agg["product_cost"] + agg["shipping_cost"]) / agg["net_sales"]
    margin_leader = agg.sort_values("margin_pct", ascending=False).iloc[0]
    cost_heaviest = agg.sort_values("cost_pct", ascending=False).iloc[0]
    return (
        f"**Business reading:** for every €1 sold, **{margin_leader['channel'].title()}** keeps the "
        f"largest share as contribution margin ({margin_leader['margin_pct']:.1%}). "
        f"**{cost_heaviest['channel'].title()}** consumes the largest share in product + shipping "
        f"({cost_heaviest['cost_pct']:.1%}), so it needs either better pricing, lower logistics cost, "
        "or lower discounts to be equally attractive."
    )


def _divergent_slices(
    agg: pd.DataFrame,
    label_col: str,
    min_net_sales: float = 0,
) -> pd.DataFrame:
    if agg.empty or len(agg) < 2:
        return pd.DataFrame()
    work = agg[agg["net_sales"] >= min_net_sales].copy()
    if len(work) < 2:
        work = agg.copy()
    work["revenue_rank"] = work["net_sales"].rank(ascending=False)
    work["margin_rank"] = work["margin_pct"].rank(ascending=False)
    work["rank_gap"] = work["revenue_rank"] - work["margin_rank"]
    return work.sort_values("rank_gap", ascending=False)


def _render_facets_explainer(entity_label: str) -> None:
    st.markdown(
        f"""
**How to read the small charts below**

Each small panel is one **{entity_label}**. Read them left-to-right as a timeline:

- **Left chart = net sales**: how much revenue that {entity_label} generated each month.
- **Right chart = margin %**: how profitable that revenue was after product cost and shipping.
- If sales go up but margin % goes down, that {entity_label} is growing with weaker profitability.
- If margin % stays stable while sales grow, that is healthier growth.
- Compare panels to separate **scale** (big revenue) from **quality** (high margin).
        """
    )


def _render_monthly_facets_takeaway(
    monthly_agg: pd.DataFrame,
    entity_col: str,
    entity_label: str,
) -> None:
    if monthly_agg.empty or entity_col not in monthly_agg.columns:
        return

    summary = (
        monthly_agg.groupby(entity_col, as_index=False)
        .agg(
            total_sales=("net_sales", "sum"),
            avg_margin=("margin_pct", "mean"),
            sales_volatility=("net_sales", "std"),
            margin_volatility=("margin_pct", "std"),
        )
        .fillna(0)
    )
    if summary.empty:
        return

    revenue_leader = summary.sort_values("total_sales", ascending=False).iloc[0]
    margin_leader = summary.sort_values("avg_margin", ascending=False).iloc[0]
    volatile_margin = summary.sort_values("margin_volatility", ascending=False).iloc[0]

    st.markdown(
        f"""
**What to look for in this view**

- Biggest {entity_label} by revenue: **{revenue_leader[entity_col]}**.
- Highest average margin %: **{margin_leader[entity_col]}**.
- Most margin variation month-to-month: **{volatile_margin[entity_col]}**.

So this view is not asking only “who is biggest?” It asks: **who is big, who is profitable,
and whose profitability is stable over time?**
        """
    )


def _build_q3_conclusion(
    channel_df: pd.DataFrame,
    country_df: pd.DataFrame,
    wholesale_df: pd.DataFrame,
) -> str:
    lines: list[str] = [
        "**Conclusion — Q03 contribution margin (current filter)**",
        "",
        "**How we built the view** (`fct_sales_enriched` → marts)",
        "- **Product cost** = `quantity_sold × dim_product.cost` (unit cost at sale; not restated on return).",
        "- **Shipping** = `fct_shipment.shipping_cost` allocated **pro-rata by line net sales within the shipment**.",
        "- **Returns** = already in **`net_sales`** (refunds reduce revenue); we do **not** add a separate "
        "return-handling cost because it is absent in source. **`quantity_sold` is not reduced** on return — "
        "margin uses post-return net sales on the mutable row (see Q02 for restatement risk).",
        "",
    ]

    if channel_df.empty:
        lines.append("_No channel data in the current filter — widen the date range or channels._")
        return "\n".join(lines)

    ch = _agg_revenue_margin(channel_df, ["channel"])
    ch_div = _divergent_slices(ch, "channel")
    top_rev = ch.sort_values("net_sales", ascending=False).iloc[0]
    top_margin = ch.sort_values("margin_pct", ascending=False).iloc[0]

    lines.append("**By channel — who makes money?**")
    lines.append(
        f"- **Largest revenue:** **{top_rev['channel'].title()}** — "
        f"€{top_rev['net_sales']:,.0f} net sales at **{top_rev['margin_pct']:.1%}** margin "
        f"(€{top_rev['contribution_margin']:,.0f} contribution margin)."
    )
    lines.append(
        f"- **Highest margin rate:** **{top_margin['channel'].title()}** — "
        f"**{top_margin['margin_pct']:.1%}** on €{top_margin['net_sales']:,.0f} net sales."
    )

    if top_rev["channel"] != top_margin["channel"]:
        lines.append(
            f"- **Revenue vs margin diverge:** the revenue leader is not the margin leader. "
            f"A net-sales chart ranks **{top_rev['channel'].title()}** first; margin % ranks "
            f"**{top_margin['channel'].title()}** first — logistics, returns, and mix explain the gap."
        )

    leaky = ch_div[ch_div["rank_gap"] <= -1].head(2)
    for _, row in leaky.iterrows():
        lines.append(
            f"- **Looks healthy on revenue, weaker on margin:** **{row['channel'].title()}** — "
            f"#{int(row['revenue_rank'])} by net sales but #{int(row['margin_rank'])} by margin % "
            f"({row['margin_pct']:.1%} vs channel blend {ch['contribution_margin'].sum() / ch['net_sales'].sum():.1%})."
        )

    if "product_cost" in ch.columns and "shipping_cost" in ch.columns:
        ch["shipping_share"] = ch["shipping_cost"] / ch["net_sales"]
        ch["product_share"] = ch["product_cost"] / ch["net_sales"]
        heavy_ship = ch.sort_values("shipping_share", ascending=False).iloc[0]
        lines.append(
            f"- **Shipping drag:** **{heavy_ship['channel'].title()}** allocates the highest share of "
            f"net sales to outbound shipping ({heavy_ship['shipping_share']:.1%} vs product cost "
            f"{heavy_ship['product_share']:.1%}) — pro-rata shipment allocation hits multi-line / distant orders."
        )

    if "return_rate" in ch.columns:
        worst_ret = ch.sort_values("return_rate", ascending=False).iloc[0]
        lines.append(
            f"- **Returns (embedded in net sales):** **{worst_ret['channel'].title()}** has the highest "
            f"return rate ({worst_ret['return_rate']:.1%}); refunds flow through `net_sales`, shrinking margin "
            f"without a separate return-cost line in this model."
        )

    lines.append("")

    if not wholesale_df.empty and "category" in wholesale_df.columns:
        cat = _agg_revenue_margin(wholesale_df, ["category"])
        cat_div = _divergent_slices(cat, "category")
        top_cat_rev = cat.sort_values("net_sales", ascending=False).iloc[0]
        lines.append("**By category (wholesale)**")
        lines.append(
            f"- **Top category by revenue:** **{top_cat_rev['category']}** — "
            f"€{top_cat_rev['net_sales']:,.0f} at **{top_cat_rev['margin_pct']:.1%}** margin."
        )
        weak_margin_top = cat.nlargest(5, "net_sales").sort_values("margin_pct").iloc[0]
        if weak_margin_top["category"] != top_cat_rev["category"]:
            lines.append(
                f"- Among high-volume categories, **{weak_margin_top['category']}** has the lowest margin % "
                f"({weak_margin_top['margin_pct']:.1%}) despite €{weak_margin_top['net_sales']:,.0f} net sales — "
                f"revenue chart looks strong; margin view says prune or reprice."
            )
        cat_leak = cat_div[cat_div["rank_gap"] <= -1].head(1)
        for _, row in cat_leak.iterrows():
            lines.append(
                f"- **Category revenue vs margin gap:** **{row['category']}** ranks #{int(row['revenue_rank'])} "
                f"on sales, #{int(row['margin_rank'])} on margin %."
            )
        lines.append("")

    if not country_df.empty and "country_name" in country_df.columns:
        co = _agg_revenue_margin(country_df, ["country_name"]).nlargest(15, "net_sales")
        if not co.empty:
            top_co = co.iloc[0]
            co_margin_leader = co.sort_values("margin_pct", ascending=False).iloc[0]
            lines.append("**By country (worth showing for wholesale geo)**")
            lines.append(
                f"- **Largest market:** **{top_co['country_name']}** — "
                f"€{top_co['net_sales']:,.0f}, margin **{top_co['margin_pct']:.1%}**."
            )
            if top_co["country_name"] != co_margin_leader["country_name"]:
                lines.append(
                    f"- **Best margin country (top 15 by sales):** **{co_margin_leader['country_name']}** "
                    f"at **{co_margin_leader['margin_pct']:.1%}** — invest where margin follows volume."
                )
            co_div = _divergent_slices(co, "country_name")
            for _, row in co_div[co_div["rank_gap"] <= -2].head(1).iterrows():
                lines.append(
                    f"- **Country revenue > margin quality:** **{row['country_name']}** — "
                    f"sales rank #{int(row['revenue_rank'])}, margin rank #{int(row['margin_rank'])} "
                    f"({row['margin_pct']:.1%} margin)."
                )
            lines.append("")

    lines.extend([
        "**What to do with this**",
        "- Use **net sales charts** for growth and mix; use **contribution margin %** to decide "
        "which channels, categories, and countries to scale.",
        "- Treat recent months as **provisional** when return rates are high (Q02) — margin can restate.",
        "- For **SKU-level** profit, extend `fct_sales_enriched` with the same cost rules; this dashboard "
        "stops at channel / wholesale category / country marts.",
    ])
    return "\n".join(lines)


def _render_margin_timelapse(channel_df: pd.DataFrame) -> None:
    st.markdown("**Time lapse — revenue and margin through the period**")
    st.caption(
        "Watch whether margin % keeps pace with net sales month by month. "
        "A rising revenue bar with a flat or falling green line means volume without profit."
    )
    fig = _revenue_margin_timelapse_fig(channel_df)
    _plotly(fig, "q3_timelapse_main")
    col1, col2 = st.columns(2)
    with col1:
        _plotly(_margin_pct_timelapse_fig(channel_df), "q3_timelapse_margin_by_channel")
    with col2:
        _plotly(_cost_stack_by_channel_fig(channel_df), "q3_cost_stack_by_channel")
    unit_takeaway = _unit_economics_takeaway(channel_df)
    if unit_takeaway:
        st.markdown(unit_takeaway)


def _render_revenue_margin_charts(
    channel_df: pd.DataFrame,
    country_df: pd.DataFrame,
) -> None:
    st.markdown("**Revenue vs margin — compare volume and profitability**")
    st.caption(
        "High net sales with lower margin % means volume without profit. "
        "Use the slice to see whether the gap is structural by channel, country, or month."
    )
    slice_by = st.radio(
        "Slice by",
        ["Channel", "Country", "Month-year"],
        horizontal=True,
        key="case_study_margin_slice",
    )

    if slice_by == "Channel":
        if channel_df.empty:
            st.info("No channel data for the current filters.")
            return
        period_col = resolve_period_col(channel_df)
        period_agg = _agg_revenue_margin(channel_df, ["channel"])
        colors = channel_color_map(period_agg["channel"])
        _plotly(
            _revenue_margin_dual_axis_fig(
                period_agg,
                "channel",
                "Channel total — net sales vs margin %",
                "Channel",
            ),
            "q3_dual_axis_channel",
        )
        _plotly(
            _revenue_margin_scatter_fig(
                period_agg,
                "channel",
                "Revenue vs margin % by channel",
                colors,
            ),
            "q3_scatter_channel",
        )
        monthly = _with_month_year(channel_df, period_col)
        monthly_agg = _agg_revenue_margin(monthly, ["channel", "month_year"])
        _render_facets_explainer("channel")
        col1, col2 = st.columns(2)
        with col1:
            _plotly(
                _faceted_monthly_fig(
                    monthly_agg,
                    "channel",
                    "net_sales",
                    "Net sales by month — channel facets",
                    colors,
                ),
                "q3_faceted_sales_channel",
            )
        with col2:
            _plotly(
                _faceted_monthly_fig(
                    monthly_agg,
                    "channel",
                    "margin_pct",
                    "Margin % by month — channel facets",
                    colors,
                ),
                "q3_faceted_margin_channel",
            )
        _render_monthly_facets_takeaway(monthly_agg, "channel", "channel")

    elif slice_by == "Country":
        if country_df.empty or "country_name" not in country_df.columns:
            st.info("No country data for the current filters.")
            return
        period_col = resolve_period_col(country_df)
        period_agg = _agg_revenue_margin(country_df, ["country_name"])
        colors = country_color_map(period_agg["country_name"])
        top = period_agg.nlargest(12, "net_sales")
        _plotly(
            _revenue_margin_dual_axis_fig(
                top,
                "country_name",
                "Country total — net sales vs margin %",
                "Country",
            ),
            "q3_dual_axis_country",
        )
        _plotly(
            _revenue_margin_scatter_fig(
                top,
                "country_name",
                "Revenue vs margin % by country",
                colors,
            ),
            "q3_scatter_country",
        )
        monthly = _with_month_year(country_df, period_col)
        monthly_agg = _agg_revenue_margin(monthly, ["country_name", "month_year"])
        top_countries = top["country_name"].tolist()
        monthly_agg = monthly_agg[monthly_agg["country_name"].isin(top_countries)]
        _render_facets_explainer("country")
        col1, col2 = st.columns(2)
        with col1:
            _plotly(
                _faceted_monthly_fig(
                    monthly_agg,
                    "country_name",
                    "net_sales",
                    "Net sales by month — country facets",
                    colors,
                ),
                "q3_faceted_sales_country",
            )
        with col2:
            _plotly(
                _faceted_monthly_fig(
                    monthly_agg,
                    "country_name",
                    "margin_pct",
                    "Margin % by month — country facets",
                    colors,
                ),
                "q3_faceted_margin_country",
            )
        _render_monthly_facets_takeaway(monthly_agg, "country_name", "country")

    else:
        if channel_df.empty:
            st.info("No data for the current filters.")
            return
        period_col = resolve_period_col(channel_df)
        monthly = _with_month_year(channel_df, period_col)
        month_agg = _agg_revenue_margin(monthly, ["month_year"])
        _plotly(
            _revenue_margin_dual_axis_fig(
                month_agg,
                "month_year",
                "Net sales vs margin % by month-year (all channels)",
                "Month-year",
            ),
            "q3_dual_axis_month",
        )
        channel_monthly = _agg_revenue_margin(monthly, ["channel", "month_year"])
        colors = channel_color_map(channel_monthly["channel"].unique())
        _render_facets_explainer("channel")
        col1, col2 = st.columns(2)
        with col1:
            _plotly(
                _faceted_monthly_fig(
                    channel_monthly,
                    "channel",
                    "net_sales",
                    "Net sales by month — channel facets",
                    colors,
                ),
                "q3_faceted_sales_month_slice",
            )
        with col2:
            _plotly(
                _faceted_monthly_fig(
                    channel_monthly,
                    "channel",
                    "margin_pct",
                    "Margin % by month — channel facets",
                    colors,
                ),
                "q3_faceted_margin_month_slice",
            )
        _render_monthly_facets_takeaway(channel_monthly, "channel", "channel")


def _channel_snapshot(df: pd.DataFrame) -> pd.DataFrame | None:
    if df.empty or "channel" not in df.columns:
        return None
    agg = df.groupby("channel", as_index=False).agg(
        net_sales=("net_sales", "sum"),
        quantity_sold=("quantity_sold", "sum"),
        quantity_returned=("quantity_returned", "sum"),
        contribution_margin=("contribution_margin", "sum"),
    )
    agg["return_rate"] = agg["quantity_returned"] / agg["quantity_sold"]
    agg["margin_pct"] = agg["contribution_margin"] / agg["net_sales"]
    agg["mix_pct"] = agg["net_sales"] / agg["net_sales"].sum()
    return agg.sort_values("net_sales", ascending=False)


def _margin_vs_revenue_gap(channel_df: pd.DataFrame) -> list[str]:
    snap = _channel_snapshot(channel_df)
    if snap is None or len(snap) < 2:
        return []
    by_revenue = snap.sort_values("net_sales", ascending=False)["channel"].tolist()
    by_margin = snap.sort_values("margin_pct", ascending=False)["channel"].tolist()
    lines = []
    if by_revenue[0] != by_margin[0]:
        top_rev = by_revenue[0]
        top_margin = by_margin[0]
        rev_row = snap[snap["channel"] == top_rev].iloc[0]
        margin_row = snap[snap["channel"] == top_margin].iloc[0]
        lines.append(
            f"In the current filter, **{top_rev.title()}** leads net sales "
            f"(€{rev_row['net_sales']:,.0f}, {rev_row['margin_pct']:.1%} margin) "
            f"but **{top_margin.title()}** leads margin rate "
            f"({margin_row['margin_pct']:.1%} on €{margin_row['net_sales']:,.0f})."
        )
    leaky = snap[snap["return_rate"] > snap["return_rate"].median()].sort_values(
        "return_rate", ascending=False,
    )
    if not leaky.empty:
        worst = leaky.iloc[0]
        lines.append(
            f"**{worst['channel'].title()}** shows the highest return rate in slice "
            f"({worst['return_rate']:.1%}) — worth checking whether growth is quality growth."
        )
    return lines


def _format_yoy(yoy: float | None) -> str:
    if yoy is None:
        return "n/a"
    sign = "+" if yoy >= 0 else ""
    return f"{sign}{yoy:.1%} YoY"


def render_q1_channel_page(
    channel_df: pd.DataFrame,
    wholesale_df: pd.DataFrame,
    channel_kpis: dict,
    wholesale_kpis: dict,
) -> None:
    st.markdown("#### Q1 — Channel sales")
    st.caption(
        "Same channel data, two different business questions: company performance vs wholesale deal planning."
    )

    st.markdown(
        """
**Question** — How is the business performing across channels?

The answer depends on who is asking.

For a **CEO**, the channel view should be an **evolutionary scorecard**: net sales over time,
YoY comparison, channel mix, return rate, and margin %. The goal is to understand whether the
business is growing, whether the growth is coming from the right channels, and whether that growth
is still healthy after returns and direct costs.

For the **Head of Wholesale**, the question is more operational: which **countries**, **partners**,
and **product categories** should be pushed in the next quarter or season? Wholesale is B2B, so the
right view is less about daily channel competition and more about geography, assortment, margin
headroom, and discount room for partner negotiations.

Important limitation: this dataset supports **commercial KPIs** and **contribution margin**, not full
financial health metrics. We can discuss net sales, YoY, returns, channel mix, product cost, shipping
allocation, and margin. We cannot calculate **EBITDA**, **EBIT**, **ROI**, **ROIC**, cash conversion, or
CAC payback because we do not have OPEX, payroll, marketing spend, assets, cash flow, or customer
acquisition costs.
        """
    )

    st.markdown("##### Tab 1 — Channel scorecard: CEO / company view")

    st.markdown(
        """
The **Channel scorecard** is the CEO view. It should answer: *is the business growing, through which
channels, and is that growth good quality?*

| Chart / KPI | Why it is needed | What we expect to learn |
| --- | --- | --- |
| **Top KPI row: Net sales + YoY** | CEO needs an evolutive numeric KPI with prior-year comparison | Whether the business is growing versus the same calendar period last year |
| **Top KPI row: Avg return rate + YoY** | Revenue can grow while return quality worsens | Whether growth is being partially cancelled by refunds |
| **Net sales by channel** | Shows absolute growth by channel over time | Which channel is driving the revenue curve |
| **Channel mix %** | Revenue can grow because one channel takes share from another | Whether the business is becoming more online, retail, wholesale, or marketplace-led |
| **Return rate by channel** | Returns are a quality signal, especially for D2C channels | Which channels generate revenue that later gets refunded |
| **Contribution margin % by channel** | Revenue is not profit | Which channels still look healthy after product cost and allocated shipping |

**Expected CEO reading:** start with the KPI row, then use Tab 1 to explain the movement:
“Net sales are up/down YoY because channel X gained/lost share; return rate improved/worsened; margin %
confirms whether the growth is profitable.”
        """
    )

    st.markdown("##### Tab 2 — Countries & wholesale: wholesale manager / B2B view")

    st.markdown(
        """
The wholesale manager does not need the same first view as the CEO. Wholesale is a **B2B negotiation**
channel: partners buy by **country**, **category**, and **season / quarter**. The question is less
“which channel won the month?” and more “where can I make deals without destroying margin?”

| Chart / KPI | Why it is needed | What we expect to learn |
| --- | --- | --- |
| **Wholesale map / top countries** | B2B deals are made by market and distributor | Which geographies deserve partner focus |
| **Country × category heatmap** | A partner may be strong in one category but weak in another | Which assortments work in each market |
| **Top wholesale categories** | Seasonal buys depend on product family | Which categories should be pushed in the next season |
| **Category trend** | Wholesale decisions are quarterly / seasonal, not only monthly | Whether a category is consistently strong or only had a one-off spike |
| **Wholesale margin %** | Discounting needs a profit floor | Which categories/countries have room for commercial discounts |
| **Wholesale return rate** | Still important, but usually less decisive than online returns | Confirm returns are not large enough to invalidate the deal economics |

**Expected wholesale reading:** start in **Countries & wholesale → Wholesale**:
“Country A is the biggest opportunity; category B is the strongest assortment; margin % gives enough / not enough
room for discounts; returns are monitored but are not the main constraint for this channel.”
        """
    )

    st.markdown("##### Why the two views are different")

    st.markdown(
        """
| Role | First question | Best dashboard section |
| --- | --- | --- |
| **CEO** | “Is the business growing, and is growth profitable?” | KPI row + **Channel scorecard** |
| **Wholesale manager** | “Where should I negotiate B2B deals next season?” | **Countries & wholesale → Wholesale** |

For the CEO, the important logic is **evolution + YoY + mix + margin**.
For wholesale, the important logic is **country + category + margin headroom**.

That is why the same dataset should not be presented as one generic channel ranking. A revenue chart can
say “online is biggest,” while the wholesale view can still say “outerwear in Spain/Germany is the best
B2B deal opportunity.”
        """
    )

    if channel_df.empty:
        st.warning("No channel data for the current filters.")
        return

    st.markdown("##### Current filter: numbers to read with Tab 1 and Tab 2")

    if channel_kpis:
        yoy_sales = _format_yoy(channel_kpis.get("net_sales_yoy"))
        yoy_returns = _format_yoy(channel_kpis.get("return_rate_yoy"))
        rr = channel_kpis.get("return_rate")
        rr_txt = f"{rr:.1%}" if rr is not None else "—"
        st.markdown(
            f"- **All channels:** €{channel_kpis.get('net_sales', 0):,.0f} net sales "
            f"({yoy_sales}) · return rate **{rr_txt}** ({yoy_returns}) · "
            f"top channel **{channel_kpis.get('top_channel', '—').title()}**"
        )

    if wholesale_kpis and not wholesale_df.empty:
        wm = wholesale_kpis.get("margin_pct")
        wm_txt = f"{wm:.1%}" if wm is not None else "—"
        wr = wholesale_kpis.get("return_rate")
        wr_txt = f"{wr:.1%}" if wr is not None else "—"
        cat_share = wholesale_kpis.get("top_category_share")
        cat_share_txt = f"{cat_share:.0%} of wholesale" if cat_share is not None else ""
        st.markdown(
            f"- **Wholesale:** €{wholesale_kpis.get('net_sales', 0):,.0f} net sales "
            f"({_format_yoy(wholesale_kpis.get('net_sales_yoy'))}) · margin **{wm_txt}** "
            f"({_format_yoy(wholesale_kpis.get('margin_pct_yoy'))}) · returns **{wr_txt}** "
            f"(lower weight than D2C) · top category **{wholesale_kpis.get('top_category', '—')}** "
            f"{cat_share_txt}"
        )

    snap = _channel_snapshot(channel_df)
    if snap is not None:
        display = snap.assign(
            net_sales=lambda d: d["net_sales"].map(lambda v: f"€{v:,.0f}"),
            mix_pct=lambda d: d["mix_pct"].map(lambda v: f"{v:.1%}"),
            return_rate=lambda d: d["return_rate"].map(lambda v: f"{v:.1%}"),
            margin_pct=lambda d: d["margin_pct"].map(lambda v: f"{v:.1%}"),
        )[["channel", "net_sales", "mix_pct", "return_rate", "margin_pct"]]
        st.dataframe(display, use_container_width=True, hide_index=True)

    if not wholesale_df.empty and "category" in wholesale_df.columns:
        cat = (
            wholesale_df.groupby("category", as_index=False)
            .agg(
                net_sales=("net_sales", "sum"),
                contribution_margin=("contribution_margin", "sum"),
                quantity_returned=("quantity_returned", "sum"),
                quantity_sold=("quantity_sold", "sum"),
            )
        )
        cat["margin_pct"] = cat["contribution_margin"] / cat["net_sales"]
        cat["return_rate"] = cat["quantity_returned"] / cat["quantity_sold"]
        cat = cat.sort_values("net_sales", ascending=False)
        st.markdown("**Wholesale — categories (for seasonal / deal planning)**")
        st.dataframe(
            cat.assign(
                net_sales=lambda d: d["net_sales"].map(lambda v: f"€{v:,.0f}"),
                margin_pct=lambda d: d["margin_pct"].map(lambda v: f"{v:.1%}"),
                return_rate=lambda d: d["return_rate"].map(lambda v: f"{v:.1%}"),
            )[["category", "net_sales", "margin_pct", "return_rate"]],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("##### Answer")
    st.markdown(
        """
- **For the CEO**, the correct answer is not only “which channel sold most.” It is: net sales evolution,
  YoY change, channel mix, return pressure, and contribution margin %. This dashboard can defend those
  KPIs, but not full financial KPIs like EBITDA or ROI.
- **For the wholesale manager**, the correct answer is operational: which countries and categories are
  attractive for B2B partners next quarter / next season, and how much margin headroom exists for discounts.
- **Returns matter differently by channel:** online returns are a bigger quality risk; wholesale returns are
  monitored, but category economics and geography are usually more important for deal design.
- **Use Tab 1 for business evolution; use Tab 2 for wholesale deal planning.**
        """
    )
    for line in _margin_vs_revenue_gap(channel_df):
        st.markdown(line)
    if snap is not None and len(snap) >= 1:
        top = snap.iloc[0]
        wholesale_row = snap[snap["channel"].str.lower() == "wholesale"] if "channel" in snap.columns else pd.DataFrame()
        online_row = snap[snap["channel"].str.lower() == "online"] if "channel" in snap.columns else pd.DataFrame()
        st.markdown(
            f"- **{top['channel'].title()}** leads net sales (€{top['net_sales']:,.0f}, "
            f"{top['margin_pct']:.1%} margin). Open **Channel scorecard** for the trend behind this number."
        )
        if not wholesale_row.empty and not online_row.empty:
            w = wholesale_row.iloc[0]
            o = online_row.iloc[0]
            st.markdown(
                f"- **Wholesale vs online:** wholesale margin **{w['margin_pct']:.1%}** and return rate "
                f"**{w['return_rate']:.1%}** vs online **{o['margin_pct']:.1%}** / **{o['return_rate']:.1%}** — "
                f"deal planning should lean on wholesale category tables, not online return dynamics."
            )


def render_q2_returns_page() -> None:
    st.markdown("#### Q2 — Net sales & late-arriving returns")
    st.caption("Why the mutable `fct_sale_order_line` breaks reporting — and the proposed fix.")
    st.markdown(
        """
**Question** — `quantity_returned` and `net_sales` update in place 30–90 days after the sale.
Design a schema that preserves **purchase date**, captures **return dates**, and supports both
**stock** and **P&L** views.
        """
    )

    st.markdown("**Evidence — what breaks today**")
    st.markdown(
        """
`production.fct_sale_order_line`: **fixed** `created_at`, **mutable** `quantity_returned` / `net_sales`,
**no** `returned_at`. One sale can return on **multiple dates**; production only keeps final totals.
        """
    )
    _render_returns_problem_charts()
    _render_returned_at_comparison()

    st.markdown("**Proposed schema — always visible because it is the answer**")
    st.markdown(
        """
| Table | Role |
| --- | --- |
| **`dim_product`** | SKU, category, cost |
| **`dim_shipment`** | shipment_id, shipping_cost, country |
| **`fct_sale_order_line_snapshot`** | Immutable sale at `sold_at` |
| **`fct_return_event`** | Append-only returns with `returned_at`, `quantity_returned_delta`, negative `net_sales_delta`, and `return_destination` |
        """
    )
    _render_returns_schema_diagram()
    st.caption("Current net sales / returned quantity are calculated by rolling up snapshot + return events in the reporting layer.")
    _render_returns_process_explanation()
    st.markdown(
        """
| Lens | Date grain | Example |
| --- | --- | --- |
| **Stock** | `returned_at` | Return in November → stock up in November |
| **Net revenue / P&L** | `sold_at` month + `net_sales_delta` | Same return → subtract revenue from September sale |
        """
    )

    st.markdown(
        """
**Answer**
- Split **immutable sale snapshot** + **append-only return events** — never overwrite the sale row.
- Store **`returned_at`** and negative **`net_sales_delta`** per event (partial returns on different dates stay visible and subtract revenue correctly).
- Attribute **net sales & margin** to the **purchase period**; attribute **stock** to **return date**.
- Dashboards need *“as first reported | as of today”* on past months while returns are still arriving.
        """
    )


def render_q3_margin_page(
    channel_df: pd.DataFrame,
    wholesale_df: pd.DataFrame,
    country_df: pd.DataFrame | None = None,
) -> None:
    country_df = country_df if country_df is not None else pd.DataFrame()

    st.markdown("#### Q3 — Contribution margin")
    st.caption(
        "Which channels and categories make money after product cost and shipping — "
        "and which look healthy on revenue only?"
    )
    st.markdown(
        """
**Question** — Build contribution margin with explicit handling of **product cost**,
**shipping allocation**, and **returns**. Slice by channel, category, country.

```
product_cost       = quantity_sold × dim_product.cost
allocated_shipping = (line net_sales / shipment net_sales) × fct_shipment.shipping_cost
contribution_margin = net_sales − product_cost − allocated_shipping
```

**Assumptions** — Returns flow through **`net_sales`** (no separate return-handling cost in source).
Shipping is **pro-rata by net sales within the shipment**. Product cost is **not** restated on return.
        """
    )

    if channel_df.empty:
        st.warning("No channel data for the current filters.")
        return

    st.markdown("**Evidence — revenue vs margin**")
    _render_revenue_margin_charts(channel_df, country_df)
    _render_margin_timelapse(channel_df)

    snap = _channel_snapshot(channel_df)
    if snap is not None:
        st.markdown("**Ranking — revenue vs margin**")
        ranked = snap.assign(
            revenue_rank=snap["net_sales"].rank(ascending=False).astype(int),
            margin_rank=snap["margin_pct"].rank(ascending=False).astype(int),
        ).sort_values("revenue_rank")
        st.dataframe(
            ranked[["channel", "revenue_rank", "margin_rank", "net_sales", "margin_pct"]].assign(
                net_sales=lambda d: d["net_sales"].map(lambda v: f"€{v:,.0f}"),
                margin_pct=lambda d: d["margin_pct"].map(lambda v: f"{v:.1%}"),
            ),
            use_container_width=True,
            hide_index=True,
        )

    if not wholesale_df.empty and "category" in wholesale_df.columns:
        cat = (
            wholesale_df.groupby("category", as_index=False)
            .agg(net_sales=("net_sales", "sum"), contribution_margin=("contribution_margin", "sum"))
        )
        cat["margin_pct"] = cat["contribution_margin"] / cat["net_sales"]
        cat = cat.sort_values("net_sales", ascending=False).head(5)
        if not cat.empty:
            st.markdown("**Wholesale categories (top 5 by net sales)**")
            st.dataframe(
                cat.assign(
                    net_sales=lambda d: d["net_sales"].map(lambda v: f"€{v:,.0f}"),
                    margin_pct=lambda d: d["margin_pct"].map(lambda v: f"{v:.1%}"),
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown(_build_q3_conclusion(channel_df, country_df, wholesale_df))


def render_case_study_tab(
    channel_df: pd.DataFrame,
    wholesale_df: pd.DataFrame,
    country_df: pd.DataFrame | None = None,
    channel_kpis: dict | None = None,
    wholesale_kpis: dict | None = None,
) -> None:
    """Legacy wrapper — prefer dedicated Q1/Q2/Q3 pages in the app tabs."""
    render_q1_channel_page(
        channel_df,
        wholesale_df,
        channel_kpis or {},
        wholesale_kpis or {},
    )
    st.divider()
    render_q2_returns_page()
    st.divider()
    render_q3_margin_page(channel_df, wholesale_df, country_df)
