from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go

from data import MAP_METRIC_OPTIONS, aggregate_countries, aggregate_wholesale_categories, resolve_period_col
from theme import (
    CONTINUOUS_COLORSCALE,
    PLOTLY_LAYOUT,
    RATE_COLORSCALE,
    category_color_map,
    channel_color_map,
    country_color_map,
)

MONETARY_METRICS = frozenset({"net_sales", "contribution_margin", "gross_sale"})
RATE_METRICS = frozenset({"return_rate", "contribution_margin_pct"})

METRIC_AXIS_LABELS = {
    "net_sales": "Net sales (€)",
    "quantity_sold": "Units sold",
    "return_rate": "Return rate",
    "contribution_margin": "Contribution margin (€)",
    "contribution_margin_pct": "Margin %",
}


def _apply_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    layout = dict(PLOTLY_LAYOUT)
    if title:
        layout["title"] = {"text": title, **PLOTLY_LAYOUT.get("title", {})}
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor="#e2e8f0", zeroline=False)
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
    return fig


def _metric_colorscale(metric: str):
    if metric in {"return_rate", "contribution_margin_pct"}:
        return RATE_COLORSCALE
    return CONTINUOUS_COLORSCALE


def _channel_colors(df):
    return channel_color_map(df["channel"].unique())


def _apply_currency_ticks(fig: go.Figure, metric: str, axis: str = "x") -> None:
    if metric not in MONETARY_METRICS:
        return
    update_axes = fig.update_xaxes if axis == "x" else fig.update_yaxes
    update_axes(tickprefix="€", tickformat=".2s", separatethousands=True)


def _apply_currency_colorbar(fig: go.Figure, metric: str) -> None:
    if metric not in MONETARY_METRICS:
        return
    fig.update_layout(
        coloraxis_colorbar=dict(
            tickprefix="€",
            tickformat=".2s",
            separatethousands=True,
        )
    )


def _rate_axis_range(metric: str, values) -> tuple[float, float] | None:
    if metric == "contribution_margin_pct":
        return (0.0, 1.0)
    if metric == "return_rate":
        if values is None or len(values) == 0:
            return (0.0, 0.25)
        max_val = float(max(values))
        upper = min(1.0, max(max_val * 1.2, 0.08))
        return (0.0, upper)
    return None


def _apply_rate_bar_axis(
    fig: go.Figure,
    metric: str,
    values,
    *,
    axis: str = "x",
    axis_label: str,
) -> None:
    update_axes = fig.update_xaxes if axis == "x" else fig.update_yaxes
    update_axes(tickformat=".1%")
    axis_range = _rate_axis_range(metric, values)
    if axis_range:
        update_axes(range=list(axis_range))
    if axis == "x":
        fig.update_traces(
            hovertemplate=f"<b>%{{y}}</b><br>{axis_label}: %{{x:.1%}}<extra></extra>",
        )
    else:
        fig.update_traces(
            hovertemplate=f"<b>%{{x}}</b><br>{axis_label}: %{{y:.1%}}<extra></extra>",
        )


def _format_metric_hover(metric: str, value: float) -> str:
    if metric in RATE_METRICS:
        return f"{value:.1%}"
    if metric in MONETARY_METRICS:
        return f"€{value:,.0f}"
    return f"{value:,.0f}"


def _period_axis(df):
    column = resolve_period_col(df)
    labels = {"period_day": "Day", "period_week": "Week", "period_month": "Month"}
    return column, labels[column]


def build_net_sales_chart(df):
    period_col, period_label = _period_axis(df)
    colors = _channel_colors(df)
    fig = px.line(
        df,
        x=period_col,
        y="net_sales",
        color="channel",
        markers=True,
        title="Net sales by channel",
        labels={period_col: period_label, "net_sales": "Net sales (€)", "channel": "Channel"},
        color_discrete_map=colors,
        category_orders={"channel": list(colors.keys())},
    )
    fig.update_layout(hovermode="x unified", legend_title_text="Channel")
    fig.update_yaxes(tickprefix="€", tickformat=".2s", separatethousands=True)
    return _apply_layout(fig, "Net sales by channel")


def build_mix_chart(df):
    period_col, period_label = _period_axis(df)
    colors = _channel_colors(df)
    fig = px.area(
        df,
        x=period_col,
        y="pct_of_total_net_sales",
        color="channel",
        title="Channel mix (% of total net sales)",
        labels={
            period_col: period_label,
            "pct_of_total_net_sales": "Share",
            "channel": "Channel",
        },
        color_discrete_map=colors,
        category_orders={"channel": list(colors.keys())},
    )
    fig.update_layout(yaxis_tickformat=".0%", hovermode="x unified")
    return _apply_layout(fig, "Channel mix (% of total net sales)")


def build_return_rate_chart(df):
    period_col, period_label = _period_axis(df)
    colors = _channel_colors(df)
    fig = px.bar(
        df.sort_values(period_col),
        x=period_col,
        y="return_rate",
        color="channel",
        barmode="group",
        title="Return rate by channel",
        labels={period_col: period_label, "return_rate": "Return rate", "channel": "Channel"},
        color_discrete_map=colors,
        category_orders={"channel": list(colors.keys())},
    )
    fig.update_layout(yaxis_tickformat=".1%", hovermode="x unified")
    return _apply_layout(fig, "Return rate by channel")


def build_margin_chart(df):
    period_col, period_label = _period_axis(df)
    colors = _channel_colors(df)
    fig = px.line(
        df,
        x=period_col,
        y="contribution_margin_pct",
        color="channel",
        markers=True,
        title="Contribution margin % by channel",
        labels={
            period_col: period_label,
            "contribution_margin_pct": "Margin %",
            "channel": "Channel",
        },
        color_discrete_map=colors,
        category_orders={"channel": list(colors.keys())},
    )
    fig.update_layout(yaxis_tickformat=".0%", hovermode="x unified")
    return _apply_layout(fig, "Contribution margin % by channel")


def build_world_map_heatmap(df, metric: str = "net_sales"):
    map_df = aggregate_countries(df, metric=metric)
    label = MAP_METRIC_OPTIONS.get(metric, metric)
    if map_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"{label} by country",
            annotations=[{
                "text": "No country data for the selected filters.",
                "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                "showarrow": False, "font": {"size": 14, "color": "#64748b"},
            }],
        )
        return _apply_layout(fig, f"{label} by country")

    metric_labels = METRIC_AXIS_LABELS
    color_label = metric_labels.get(metric, label)
    country_colors = country_color_map(map_df["country_name"])
    metric_display = map_df[metric].map(lambda value: _format_metric_hover(metric, value))

    fig = px.choropleth(
        map_df,
        locations="iso_alpha",
        locationmode="ISO-3",
        color="country_name",
        color_discrete_map=country_colors,
        category_orders={"country_name": sorted(country_colors.keys())},
        title=f"{label} by country",
        labels={"country_name": "Country"},
        hover_name="country_name",
    )
    fig.update_traces(
        customdata=metric_display,
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            f"{color_label}: %{{customdata}}<extra></extra>"
        ),
    )
    fig.update_layout(
        showlegend=False,
        title=dict(text=f"{label} by country", x=0.02, xanchor="left"),
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#94a3b8",
            coastlinewidth=0.6,
            showland=True,
            landcolor="#f1f5f9",
            showocean=True,
            oceancolor="#e0f2fe",
            showlakes=True,
            lakecolor="#e0f2fe",
            showcountries=True,
            countrycolor="#cbd5e1",
            bgcolor="rgba(0,0,0,0)",
            projection_type="robinson",
            lonaxis=dict(showgrid=False),
            lataxis=dict(showgrid=False),
        ),
        margin=dict(l=0, r=0, t=56, b=0),
        height=480,
    )
    return _apply_layout(fig, f"{label} by country")


def build_country_bar_chart(df, metric: str = "net_sales", top_n: int = 10):
    map_df = aggregate_countries(df, metric=metric).head(top_n)
    label = MAP_METRIC_OPTIONS.get(metric, metric)
    if map_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Top {top_n} countries · {label}",
            annotations=[{
                "text": "No country data for the selected filters.",
                "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                "showarrow": False, "font": {"size": 14, "color": "#64748b"},
            }],
        )
        return _apply_layout(fig, f"Top {top_n} countries")

    axis_label = METRIC_AXIS_LABELS.get(metric, label)
    country_colors = country_color_map(map_df["country_name"])
    metric_display = map_df[metric].map(lambda value: _format_metric_hover(metric, value))
    fig = px.bar(
        map_df.sort_values(metric),
        x=metric,
        y="country_name",
        orientation="h",
        title=f"Top {top_n} countries · {label}",
        labels={"country_name": "Country", metric: axis_label},
        color="country_name",
        color_discrete_map=country_colors,
        custom_data=[metric_display],
    )
    fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
    if metric in RATE_METRICS:
        _apply_rate_bar_axis(fig, metric, map_df[metric], axis="x", axis_label=axis_label)
        fig.update_traces(
            hovertemplate=f"<b>%{{y}}</b><br>{axis_label}: %{{customdata[0]}}<extra></extra>",
        )
    else:
        _apply_currency_ticks(fig, metric, axis="x")
        fig.update_traces(
            hovertemplate=f"<b>%{{y}}</b><br>{axis_label}: %{{customdata[0]}}<extra></extra>",
        )
    return _apply_layout(fig, f"Top {top_n} countries")


def build_wholesale_category_bar(df, metric: str = "net_sales", top_n: int = 10):
    cat_df = aggregate_wholesale_categories(df, metric=metric).head(top_n)
    label = MAP_METRIC_OPTIONS.get(metric, metric)
    if cat_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Top {top_n} categories · {label}",
            annotations=[{
                "text": "No wholesale data for the selected filters.",
                "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                "showarrow": False, "font": {"size": 14, "color": "#64748b"},
            }],
        )
        return _apply_layout(fig, f"Top {top_n} categories")

    axis_label = METRIC_AXIS_LABELS.get(metric, label)
    category_colors = category_color_map(cat_df["category"])
    metric_display = cat_df[metric].map(lambda value: _format_metric_hover(metric, value))
    fig = px.bar(
        cat_df.sort_values(metric),
        x=metric,
        y="category",
        orientation="h",
        title=f"Top {top_n} wholesale categories · {label}",
        labels={"category": "Category", metric: axis_label},
        color="category",
        color_discrete_map=category_colors,
        custom_data=[metric_display],
    )
    fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
    if metric in RATE_METRICS:
        _apply_rate_bar_axis(fig, metric, cat_df[metric], axis="x", axis_label=axis_label)
        fig.update_traces(
            hovertemplate=f"<b>%{{y}}</b><br>{axis_label}: %{{customdata[0]}}<extra></extra>",
        )
    else:
        _apply_currency_ticks(fig, metric, axis="x")
        fig.update_traces(
            hovertemplate=f"<b>%{{y}}</b><br>{axis_label}: %{{customdata[0]}}<extra></extra>",
        )
    return _apply_layout(fig, f"Top {top_n} categories")


def build_wholesale_country_category_heatmap(df, metric: str = "net_sales"):
    label = MAP_METRIC_OPTIONS.get(metric, metric)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Wholesale heatmap: country × category · {label}",
            annotations=[{
                "text": "No wholesale data for the selected filters.",
                "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                "showarrow": False, "font": {"size": 14, "color": "#64748b"},
            }],
        )
        return _apply_layout(fig, "Wholesale country × category")

    pivot = df.pivot_table(
        index="country_name",
        columns="category",
        values=metric,
        aggfunc="sum",
        fill_value=0,
    )
    color_label = METRIC_AXIS_LABELS.get(metric, label)
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=_metric_colorscale(metric),
        title=f"Wholesale heatmap: country × category · {label}",
        labels={"x": "Category", "y": "Country", "color": color_label},
    )
    colorbar = dict(thickness=14, len=0.75, outlinecolor="#e2e8f0")
    if metric in RATE_METRICS:
        colorbar["tickformat"] = ".0%"
    elif metric in MONETARY_METRICS:
        colorbar["tickprefix"] = "€"
        colorbar["tickformat"] = ".2s"
        colorbar["separatethousands"] = True
    fig.update_layout(coloraxis_colorbar=colorbar)
    return _apply_layout(fig, "Wholesale country × category")


def build_wholesale_category_trend(df, metric: str = "net_sales"):
    label = MAP_METRIC_OPTIONS.get(metric, metric)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Wholesale trend by category · {label}",
            annotations=[{
                "text": "No wholesale data for the selected filters.",
                "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                "showarrow": False, "font": {"size": 14, "color": "#64748b"},
            }],
        )
        return _apply_layout(fig, "Wholesale category trend")

    if metric in RATE_METRICS:
        trend = df.groupby(["period_month", "category"], as_index=False).agg(
            quantity_sold=("quantity_sold", "sum"),
            quantity_returned=("quantity_returned", "sum"),
        )
        trend[metric] = trend["quantity_returned"] / trend["quantity_sold"]
    elif metric == "contribution_margin_pct":
        trend = df.groupby(["period_month", "category"], as_index=False).agg(
            net_sales=("net_sales", "sum"),
            contribution_margin=("contribution_margin", "sum"),
        )
        trend[metric] = trend["contribution_margin"] / trend["net_sales"]
    else:
        trend = df.groupby(["period_month", "category"], as_index=False)[metric].sum()

    axis_label = METRIC_AXIS_LABELS.get(metric, label)
    fig = px.line(
        trend.sort_values("period_month"),
        x="period_month",
        y=metric,
        color="category",
        markers=True,
        title=f"Wholesale trend by category · {label}",
        labels={"period_month": "Month", metric: axis_label, "category": "Category"},
    )
    fig.update_layout(hovermode="x unified", legend_title_text="Category")
    if metric in RATE_METRICS:
        axis_range = _rate_axis_range(metric, trend[metric])
        fig.update_yaxes(tickformat=".1%")
        if axis_range:
            fig.update_yaxes(range=list(axis_range))
    elif metric in MONETARY_METRICS:
        fig.update_yaxes(tickprefix="€", tickformat=".2s", separatethousands=True)
    return _apply_layout(fig, "Wholesale category trend")


def build_country_channel_heatmap(df):
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Net sales heatmap: country × channel",
            annotations=[{
                "text": "No country data for the selected filters.",
                "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                "showarrow": False, "font": {"size": 14, "color": "#64748b"},
            }],
        )
        return _apply_layout(fig, "Net sales heatmap: country × channel")

    pivot = df.pivot_table(
        index="country_name",
        columns="channel",
        values="net_sales",
        aggfunc="sum",
        fill_value=0,
    )
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=CONTINUOUS_COLORSCALE,
        title="Net sales heatmap: country × channel",
        labels={"x": "Channel", "y": "Country", "color": "Net sales (€)"},
    )
    fig.update_layout(
        coloraxis_colorbar=dict(
            tickprefix="€",
            tickformat=".2s",
            separatethousands=True,
        )
    )
    return _apply_layout(fig, "Net sales heatmap: country × channel")
