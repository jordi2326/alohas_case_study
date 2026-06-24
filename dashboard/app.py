import html
import re
import matplotlib.colors as mcolors
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from case_study import render_q1_channel_page, render_q2_returns_page, render_q3_margin_page
from charts import (
    build_channel_rate_comparison,
    build_country_bar_chart,
    build_country_channel_heatmap,
    build_country_channel_category_heatmap,
    build_margin_chart,
    build_mix_chart,
    build_net_sales_chart,
    build_return_rate_chart,
    build_wholesale_category_bar,
    build_wholesale_category_trend,
    build_wholesale_country_category_heatmap,
    build_world_map_heatmap,
)
from data import (
    MAP_METRIC_OPTIONS,
    DATAMART_DATASET,
    PROJECT_ID,
    SOURCE_DATASET,
    compute_channel_kpis,
    compute_country_kpi,
    compute_wholesale_kpis,
    analytics_data_source_label,
    clamp_period,
    using_cached_data,
    data_bounds,
    filter_data,
    filter_wholesale_data,
    format_period_label,
    format_yoy_delta,
    intersect_period,
    latest_period,
    load_channel_performance,
    load_category_country_channel_performance,
    load_country_performance,
    load_data_quality_detail,
    load_data_quality_summary,
    load_wholesale_performance,
    match_period_preset,
    period_for_preset,
    picker_date_bounds,
    preset_granularity,
    prepare_data_quality_detail_table,
    prepare_data_quality_summary_table,
    prepare_summary_table,
    prepare_wholesale_summary_table,
    prior_year_period,
    resolve_period_col,
    PERIOD_PRESETS,
)
from insights import (
    build_all_channel_category_insights,
    build_channel_insights,
    build_country_insights,
    build_wholesale_insights,
)
from queries import DATA_QUALITY_DETAIL_QUERIES
from theme import (
    ACCENT,
    ACCENT_2,
    BAD,
    CHART_GUIDES,
    GOOD,
    KPI_DETAILS,
    METRIC_TOOLTIPS,
    STREAMLIT_CSS,
    TABLE_EMBED_CSS,
    WARN,
    channel_color_map,
)

BLUE_TABLE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "brand_blue", ["#ffffff", "#eff6ff", "#bfdbfe", "#93c5fd"]
)
RATE_TABLE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "brand_rate", ["#ffffff", "#ecfdf5", "#fef3c7", "#fee2e2"]
)
MIX_TABLE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "brand_mix", ["#ffffff", "#f5f3ff", "#ede9fe", "#ddd6fe"]
)

TABLE_STYLES = [
    {
        "selector": "thead th",
        "props": [
            ("background-color", "#f8fafc"),
            ("color", "#64748b"),
            ("font-size", "0.72rem"),
            ("font-weight", "700"),
            ("text-transform", "uppercase"),
            ("letter-spacing", "0.05em"),
            ("padding", "11px 14px"),
            ("border-bottom", "2px solid #e2e8f0"),
            ("white-space", "nowrap"),
        ],
    },
    {
        "selector": "tbody td",
        "props": [
            ("padding", "10px 14px"),
            ("font-size", "0.84rem"),
            ("color", "#334155"),
            ("border-bottom", "1px solid #f1f5f9"),
        ],
    },
    {
        "selector": "tbody tr:last-child td",
        "props": [("border-bottom", "none")],
    },
]


def parse_date_range(date_range, min_date, max_date):
    if isinstance(date_range, tuple):
        if len(date_range) == 2 and all(date_range):
            start_date, end_date = date_range
        elif len(date_range) >= 1 and date_range[0]:
            start_date = end_date = date_range[0]
        else:
            start_date, end_date = min_date, max_date
    else:
        start_date = end_date = date_range
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def _info_tooltip_html(*, definition: str = "", guide: str = "", details: str = "") -> str:
    sections = []
    if definition:
        sections.append(f"<p><strong>Definition:</strong> {html.escape(definition)}</p>")
    if details:
        sections.append(
            f"<p><strong>How it is calculated:</strong> {html.escape(details)}</p>"
        )
    if guide:
        sections.append(f"<p><strong>How to read it:</strong> {html.escape(guide)}</p>")
    if not sections:
        return ""
    return (
        '<span class="info-tip" aria-label="Metric information">'
        '<span class="info-tip-icon">?</span>'
        f'<span class="info-tip-content">{"".join(sections)}</span>'
        "</span>"
    )


def panel_header(
    title: str,
    *,
    definition: str = "",
    guide: str = "",
    details: str = "",
) -> None:
    tip = _info_tooltip_html(definition=definition, guide=guide, details=details)
    st.markdown(
        f'<div class="panel-header">'
        f'<span class="panel-header-title">{html.escape(title)}</span>'
        f"{tip}"
        f"</div>",
        unsafe_allow_html=True,
    )


def chart_panel(
    title: str,
    metric_key: str,
    fig,
    *,
    guide_key: str | None = None,
    chart_key: str | None = None,
) -> None:
    guide = CHART_GUIDES.get(guide_key or metric_key, "")
    definition = METRIC_TOOLTIPS.get(metric_key, "")
    with st.container(border=True):
        panel_header(title, definition=definition, guide=guide)
        st.plotly_chart(fig, use_container_width=True, key=chart_key)


def style_summary_table(display: pd.DataFrame, by_country: bool):
    mix_col = "Mix % (channel)" if by_country else "Mix %"
    formats = {
        "Net sales": "€{:,.0f}",
        "Units sold": "{:,.0f}",
        "Return rate": "{:.1%}",
        "Margin %": "{:.1%}",
        mix_col: "{:.1%}",
    }
    if not by_country:
        formats["Net sales YoY"] = "{:+.1%}"

    numeric_cols = [
        col
        for col in [
            "Net sales",
            "Units sold",
            "Return rate",
            "Margin %",
            mix_col,
            "Net sales YoY",
        ]
        if col in display.columns
    ]
    text_cols = [col for col in display.columns if col not in numeric_cols]

    styled = (
        display.style.format(formats, na_rep="—")
        .set_table_attributes('class="data-table"')
        .set_table_styles(TABLE_STYLES, overwrite=False)
        .set_properties(subset=numeric_cols, **{"text-align": "right"})
        .set_properties(subset=text_cols, **{"text-align": "left"})
    )

    if not display.empty and "Return rate" in display.columns:
        max_return = max(display["Return rate"].max(), 0.05)
        styled = styled.background_gradient(
            subset=["Return rate"],
            cmap=RATE_TABLE_CMAP,
            vmin=0,
            vmax=max_return,
        )

    if not display.empty and "Margin %" in display.columns:
        max_margin = max(display["Margin %"].max(), 0.05)
        styled = styled.background_gradient(
            subset=["Margin %"],
            cmap=BLUE_TABLE_CMAP,
            vmin=0,
            vmax=max_margin,
        )

    if not display.empty and mix_col in display.columns:
        max_mix = max(display[mix_col].max(), 0.05)
        styled = styled.background_gradient(
            subset=[mix_col],
            cmap=MIX_TABLE_CMAP,
            vmin=0,
            vmax=max_mix,
        )

    return styled.hide(axis="index")


def style_wholesale_table(display: pd.DataFrame):
    formats = {
        "Net sales": "€{:,.0f}",
        "Units sold": "{:,.0f}",
        "Return rate": "{:.1%}",
        "Margin %": "{:.1%}",
        "Mix % (wholesale)": "{:.1%}",
    }
    for col in formats:
        if col in display.columns:
            display[col] = pd.to_numeric(display[col], errors="coerce")
    numeric_cols = [col for col in formats if col in display.columns]
    text_cols = [col for col in display.columns if col not in numeric_cols]
    styled = (
        display.style.format(formats, na_rep="—")
        .set_table_attributes('class="data-table"')
        .set_table_styles(TABLE_STYLES, overwrite=False)
        .set_properties(subset=numeric_cols, **{"text-align": "right"})
        .set_properties(subset=text_cols, **{"text-align": "left"})
    )
    if not display.empty and "Return rate" in display.columns:
        max_return = max(display["Return rate"].max(), 0.05)
        styled = styled.background_gradient(
            subset=["Return rate"],
            cmap=RATE_TABLE_CMAP,
            vmin=0,
            vmax=max_return,
        )
    if not display.empty and "Margin %" in display.columns:
        max_margin = max(display["Margin %"].max(), 0.05)
        styled = styled.background_gradient(
            subset=["Margin %"],
            cmap=BLUE_TABLE_CMAP,
            vmin=0,
            vmax=max_margin,
        )
    return styled.hide(axis="index")


def _styler_to_embed(styled) -> str:
    html_doc = styled.to_html()
    styles = "".join(re.findall(r"<style[^>]*>.*?</style>", html_doc, flags=re.DOTALL))
    table_match = re.search(r"<table[^>]*>.*?</table>", html_doc, flags=re.DOTALL)
    table = table_match.group(0) if table_match else html_doc
    return f"{styles}{table}"


def render_styled_table(
    styled,
    height: int = 420,
    *,
    scroll_max_height: int | None = None,
    table_class: str = "data-table-scroll",
) -> None:
    max_height = scroll_max_height or height
    embed_css = TABLE_EMBED_CSS.replace("max-height: 420px", f"max-height: {max_height}px")
    table_html = _styler_to_embed(styled)
    page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{embed_css}</style>
</head>
<body>
<div class="{table_class}">{table_html}</div>
</body>
</html>"""
    components.html(page, height=height + 16, scrolling=False)


def render_inline_styled_table(styled, *, css_class: str = "dq-inline-table") -> None:
    html_doc = styled.to_html()
    styles = "".join(re.findall(r"<style[^>]*>.*?</style>", html_doc, flags=re.DOTALL))
    table_match = re.search(r"<table[^>]*>.*?</table>", html_doc, flags=re.DOTALL)
    table = table_match.group(0) if table_match else html_doc
    st.markdown(
        f'{styles}<div class="{css_class}">{table}</div>',
        unsafe_allow_html=True,
    )


def _data_quality_table_height(row_count: int, *, row_px: int = 44, header_px: int = 72) -> int:
    return min(640, max(280, header_px + row_count * row_px))


def render_data_table(
    df,
    by_country: bool = False,
    *,
    title: str,
    metric_key: str,
    guide_key: str,
) -> None:
    guide = CHART_GUIDES.get(guide_key, "")
    definition = METRIC_TOOLTIPS.get(metric_key, "")
    with st.container(border=True):
        panel_header(title, definition=definition, guide=guide)
        if df.empty:
            st.info("No rows for the selected filters.")
            return
        display = prepare_summary_table(df, by_country)
        period_column = display.columns[0]
        sort_cols = [col for col in [period_column, "Net sales"] if col in display.columns]
        if sort_cols:
            display = display.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        row_count = len(display)
        st.markdown(
            f'<p class="data-table-meta">{row_count:,} rows · hover rows for highlight · '
            f"scroll for more</p>",
            unsafe_allow_html=True,
        )
        render_styled_table(style_summary_table(display, by_country))


def render_wholesale_table(
    df,
    *,
    title: str,
    guide_key: str,
) -> None:
    guide = CHART_GUIDES.get(guide_key, "")
    definition = METRIC_TOOLTIPS.get("Wholesale net sales", "")
    with st.container(border=True):
        panel_header(title, definition=definition, guide=guide)
        if df.empty:
            st.info("No wholesale rows for the selected filters.")
            return
        display = prepare_wholesale_summary_table(df)
        sort_cols = [col for col in ["Month", "Net sales"] if col in display.columns]
        if sort_cols:
            display = display.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        st.markdown(
            f'<p class="data-table-meta">{len(display):,} rows · hover rows for highlight · '
            f"scroll for more</p>",
            unsafe_allow_html=True,
        )
        render_styled_table(style_wholesale_table(display))


def style_data_quality_summary(display: pd.DataFrame):
    formats = {
        "Affected rows": "{:,.0f}",
        "% of table": "{:.2%}",
    }
    numeric_cols = [col for col in formats if col in display.columns]
    text_cols = [col for col in display.columns if col not in numeric_cols]
    styled = (
        display.style.format(formats, na_rep="—")
        .set_table_attributes('class="data-table"')
        .set_table_styles(TABLE_STYLES, overwrite=False)
        .set_properties(subset=numeric_cols, **{"text-align": "right"})
        .set_properties(subset=text_cols, **{"text-align": "left"})
    )
    if not display.empty and "Severity" in display.columns:
        severity_colors = {
            "High": "#fee2e2",
            "Medium": "#fef3c7",
            "Low": "#ecfdf5",
        }
        styled = styled.map(
            lambda value: f"background-color: {severity_colors.get(value, '')}",
            subset=["Severity"],
        )
    wrap_cols = [
        col for col in ("Record source", "Checked against", "Check rule")
        if col in display.columns
    ]
    if wrap_cols:
        styled = styled.set_properties(
            subset=wrap_cols,
            **{"white-space": "normal", "word-break": "break-word", "min-width": "140px"},
        )
    return styled.hide(axis="index")


def style_data_quality_detail(display: pd.DataFrame):
    formats = {
        "Gross sale": "€{:,.2f}",
        "Net sales": "€{:,.2f}",
        "Units sold": "{:,.0f}",
        "Units returned": "{:,.0f}",
        "Shipping cost": "€{:,.2f}",
        "Base price": "€{:,.2f}",
        "Cost": "€{:,.2f}",
    }
    numeric_cols = [col for col in formats if col in display.columns]
    text_cols = [col for col in display.columns if col not in numeric_cols]
    return (
        display.style.format(formats, na_rep="—")
        .set_table_attributes('class="data-table"')
        .set_table_styles(TABLE_STYLES, overwrite=False)
        .set_properties(subset=numeric_cols, **{"text-align": "right"})
        .set_properties(subset=text_cols, **{"text-align": "left"})
        .hide(axis="index")
    )


def render_data_quality_tab() -> None:
    st.markdown("#### Source data quality")
    st.caption(
        f"Checks on raw **`{PROJECT_ID}.{SOURCE_DATASET}`** tables. "
        f"Dashboard KPIs use cleaned **`{PROJECT_ID}.{DATAMART_DATASET}`** models "
        f"that exclude rows failing these rules."
    )
    try:
        summary = get_data_quality_summary()
    except Exception as exc:
        st.error("Could not run data quality checks against BigQuery.")
        st.exception(exc)
        return

    if summary.empty:
        st.success("No source data quality checks configured.")
        return

    failing = summary[summary["row_count"] > 0] if "row_count" in summary.columns else summary
    high_count = int((failing["severity"] == "High").sum()) if not failing.empty else 0
    total_rows = int(failing["row_count"].sum()) if not failing.empty else 0
    if failing.empty:
        st.success("All source data quality checks passed.")
    else:
        st.warning(
            f"Found **{len(failing)}** issue type(s) affecting **{total_rows:,}** source rows "
            f"({high_count} high severity)."
        )
        order_line_source = f"{PROJECT_ID}.{SOURCE_DATASET}.fct_sale_order_line"
        join_checks = failing[
            failing["issue_type"].isin(["orphan_sku", "orphan_shipment"])
        ]
        if not join_checks.empty:
            with st.container(border=True):
                st.markdown("**Shared record source for active join checks**")
                st.code(order_line_source, language=None)
                for _, row in join_checks.iterrows():
                    against = row.get("validated_against", "—")
                    st.markdown(
                        f"- **{row['issue_description']}** → missing in `{against}`"
                    )

    summary_display = prepare_data_quality_summary_table(summary)
    with st.container(border=True):
        panel_header(
            "Quality issues summary",
            definition="Record source and lookup table for each check.",
            guide="Both orphan checks read from fct_sale_order_line and validate against another table.",
        )
        st.markdown(
            f'<p class="data-table-meta">{len(summary_display):,} checks · '
            f'{len(failing):,} with issues</p>',
            unsafe_allow_html=True,
        )
        render_inline_styled_table(style_data_quality_summary(summary_display))

    st.markdown("#### Examples by check")
    sample_limit = 8
    for _, issue_row in summary.iterrows():
        issue_type = issue_row["issue_type"]
        issue_count = int(issue_row["row_count"])
        issue_label = issue_row["issue_description"]
        severity = issue_row["severity"]
        checked_in = issue_row.get("checked_in", "")
        check_rule = issue_row.get("check_rule", "")
        source_location = issue_row.get("source_location", "")
        validated_against = issue_row.get("validated_against", "—")
        status = f"**{issue_count:,} rows**" if issue_count else "✓ No issues"
        with st.expander(f"{issue_label} · {severity} · {status}", expanded=issue_count > 0):
            st.markdown(
                f"**Record source:** `{source_location}`  \n"
                f"**Checked against:** `{validated_against}`  \n"
                f"**Check rule:** `{check_rule}`  \n"
                f"**SQL context:** {checked_in}"
            )
            if issue_count == 0:
                st.success("No example rows — this check passed.")
                continue
            if issue_type not in DATA_QUALITY_DETAIL_QUERIES:
                st.info("No sample query available for this check.")
                continue
            detail = get_data_quality_detail(issue_type, limit=sample_limit)
            detail_display = prepare_data_quality_detail_table(detail)
            if detail_display.empty:
                st.info("No sample rows returned.")
                continue
            st.markdown(
                f'<p class="data-table-meta">Showing up to {len(detail_display):,} example rows</p>',
                unsafe_allow_html=True,
            )
            render_inline_styled_table(style_data_quality_detail(detail_display))
            st.download_button(
                f"Download {issue_type} sample CSV",
                data=detail.to_csv(index=False).encode("utf-8"),
                file_name=f"data_quality_{issue_type}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"download_{issue_type}",
            )

    with st.expander("Impact on analytics"):
        st.markdown(
            f"""
            Rows failing these checks are **excluded in dbt gold models** and do not reach
            `{PROJECT_ID}.{DATAMART_DATASET}`.

            - **Orphan SKU** — excluded; requires a matching `dim_product` row with cost.
            - **Orphan shipment** — excluded; requires a matching `fct_shipment` row with country.
            - **Returns exceed sold** — excluded from order lines.
            - **Negative net sales / zero quantity sold** — excluded from order lines.
            - **Null country / null cost** — excluded from shipment and product gold tables.
            """
        )


def render_wholesale_dashboard(
    wholesale_df: pd.DataFrame,
    *,
    start_date,
    end_date,
    selected_countries: list[str],
    map_metric: str,
) -> None:
    st.markdown("#### Wholesale dashboard")
    st.caption(
        "Country and **category** performance for the wholesale channel. "
        "Filters use the sidebar period and country selection."
    )

    wholesale_overlap = intersect_period(
        start_date, end_date, wholesale_min_date, wholesale_max_date,
    )
    if wholesale_overlap:
        w_start, w_end = wholesale_overlap
    else:
        w_start, w_end = wholesale_min_date, wholesale_max_date

    if not wholesale_overlap:
        st.info(
            f"Wholesale data runs **{wholesale_min_date.strftime('%b %Y')} – "
            f"{wholesale_max_date.strftime('%b %Y')}**. Showing the latest available wholesale range."
        )

    selected_wholesale_categories = st.multiselect(
        "Category",
        wholesale_categories,
        default=wholesale_categories,
        key="wholesale_categories",
    )
    if not selected_wholesale_categories:
        st.warning("Select at least one category.")
        return

    filtered_wholesale = filter_wholesale_data(
        wholesale_df,
        w_start,
        w_end,
        countries=selected_countries,
        categories=selected_wholesale_categories,
    )
    wholesale_kpis = compute_wholesale_kpis(
        wholesale_df,
        w_start,
        w_end,
        countries=selected_countries,
        categories=selected_wholesale_categories,
    )

    w1, w2, w3, w4, w5 = st.columns(5)
    with w1:
        ws_delta, ws_tone = kpi_delta(wholesale_kpis["net_sales_yoy"])
        render_kpi_card(
            "Wholesale net sales",
            f"€{wholesale_kpis['net_sales']:,.0f}",
            ws_delta,
            tone=ws_tone,
            metric_key="Wholesale net sales",
        )
    with w2:
        wr = wholesale_kpis["return_rate"]
        wr_value = f"{wr:.1%}" if wr is not None else "—"
        wr_delta, wr_tone = kpi_delta(wholesale_kpis["return_rate_yoy"])
        render_kpi_card(
            "Wholesale return rate",
            wr_value,
            wr_delta,
            tone=wr_tone,
            metric_key="Wholesale return rate",
        )
    with w3:
        wm = wholesale_kpis["margin_pct"]
        wm_value = f"{wm:.1%}" if wm is not None else "—"
        wm_delta, wm_tone = kpi_delta(wholesale_kpis["margin_pct_yoy"])
        render_kpi_card(
            "Wholesale margin",
            wm_value,
            wm_delta,
            tone=wm_tone,
            metric_key="Wholesale margin",
        )
    with w4:
        country_share = wholesale_kpis["top_country_share"]
        share_text = f" ({country_share:.0%} of wholesale)" if country_share else ""
        render_kpi_card(
            "Top wholesale country",
            wholesale_kpis["top_country"],
            metric_key="Top wholesale country",
            extra_detail=share_text.strip(),
        )
    with w5:
        cat_share = wholesale_kpis["top_category_share"]
        cat_text = f" ({cat_share:.0%} of wholesale)" if cat_share else ""
        render_kpi_card(
            "Top wholesale category",
            wholesale_kpis["top_category"],
            metric_key="Top wholesale category",
            extra_detail=cat_text.strip(),
        )

    if filtered_wholesale.empty:
        st.warning("No wholesale rows for the selected period, country, and category filters.")
        return

    wholesale_map_label = MAP_METRIC_OPTIONS.get(map_metric, map_metric)
    chart_panel(
        f"Wholesale map · {wholesale_map_label}",
        "Map metric",
        build_world_map_heatmap(filtered_wholesale, metric=map_metric),
        guide_key="Map metric",
        chart_key="wholesale_map",
    )
    wleft, wright = st.columns(2)
    with wleft:
        chart_panel(
            f"Top wholesale countries · {wholesale_map_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_country_bar_chart(filtered_wholesale, metric=map_metric),
            guide_key="Wholesale country bar",
            chart_key="wholesale_country_bar",
        )
    with wright:
        chart_panel(
            f"Top wholesale categories · {wholesale_map_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_wholesale_category_bar(filtered_wholesale, metric=map_metric),
            guide_key="Wholesale category bar",
            chart_key="wholesale_category_bar",
        )
    wrow2_left, wrow2_right = st.columns(2)
    with wrow2_left:
        chart_panel(
            f"Country × category · {wholesale_map_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_wholesale_country_category_heatmap(filtered_wholesale, metric=map_metric),
            guide_key="Wholesale country × category",
            chart_key="wholesale_country_category_heatmap",
        )
    with wrow2_right:
        chart_panel(
            f"Category trend · {wholesale_map_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_wholesale_category_trend(filtered_wholesale, metric=map_metric),
            guide_key="Wholesale category trend",
            chart_key="wholesale_category_trend",
        )
    render_wholesale_table(
        filtered_wholesale,
        title="Wholesale detail by country and category",
        guide_key="Wholesale table",
    )
    wholesale_pos, wholesale_neg, wholesale_neu = build_wholesale_insights(
        filtered_wholesale,
        map_metric=map_metric,
    )
    render_insights_footer(
        "Wholesale insights",
        wholesale_pos,
        wholesale_neg,
        wholesale_neu,
    )


def filter_category_country_channel_data(
    df: pd.DataFrame,
    start_date,
    end_date,
    *,
    channels: list[str],
    countries: list[str],
    categories: list[str],
) -> pd.DataFrame:
    if df.empty:
        return df
    mask = (
        (df["period_month"] >= pd.Timestamp(start_date))
        & (df["period_month"] <= pd.Timestamp(end_date))
        & (df["channel"].isin(channels))
        & (df["country"].isin(countries))
        & (df["category"].isin(categories))
    )
    return df.loc[mask].copy()


def render_global_country_channel_category(
    category_df: pd.DataFrame,
    _wholesale_df: pd.DataFrame,
    *,
    start_date,
    end_date,
    selected_channels: list[str],
    selected_countries: list[str],
    map_metric: str,
) -> None:
    st.markdown("#### All channels · country × category")
    st.caption(
        "Compare categories by market across the selected sales channels."
    )
    if category_df.empty:
        st.info(
            "All-channel category data could not be auto-loaded yet. Check BigQuery permissions "
            "or run `python dashboard/export_cache.py` once to refresh the local cache."
        )
        return

    available_channels = sorted(category_df["channel"].dropna().unique())
    selected_view_channels = [
        channel for channel in selected_channels
        if channel in available_channels
    ]
    if not selected_view_channels:
        selected_view_channels = available_channels

    selected_view_channels = st.multiselect(
        "Channels",
        available_channels,
        default=selected_view_channels,
        key="global_country_channel_channels",
        disabled=len(available_channels) == 1,
    )
    if not selected_view_channels:
        st.warning("Select at least one channel.")
        return

    categories = sorted(category_df["category"].dropna().unique())
    selected_categories = st.multiselect(
        "Categories",
        categories,
        default=categories,
        key="global_country_channel_categories",
    )
    if not selected_categories:
        st.warning("Select at least one category.")
        return

    filtered_global = filter_category_country_channel_data(
        category_df,
        start_date,
        end_date,
        channels=selected_view_channels,
        countries=selected_countries,
        categories=selected_categories,
    )
    if filtered_global.empty:
        st.warning("No country × channel × category rows for the selected filters.")
        return

    metric_label = MAP_METRIC_OPTIONS.get(map_metric, map_metric)
    summary = (
        filtered_global.groupby(["country_name", "channel", "category"], as_index=False)
        .agg(
            net_sales=("net_sales", "sum"),
            quantity_sold=("quantity_sold", "sum"),
            quantity_returned=("quantity_returned", "sum"),
            contribution_margin=("contribution_margin", "sum"),
        )
    )
    summary["return_rate"] = summary["quantity_returned"] / summary["quantity_sold"]
    summary["margin_pct"] = summary["contribution_margin"] / summary["net_sales"]

    total_sales = summary["net_sales"].sum()
    total_units = summary["quantity_sold"].sum()
    total_returned = summary["quantity_returned"].sum()
    total_margin = summary["contribution_margin"].sum()
    global_return_rate = total_returned / total_units if total_units else None
    global_margin_pct = total_margin / total_sales if total_sales else None
    top_country = (
        summary.groupby("country_name", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )
    top_category = (
        summary.groupby("category", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi_card("Selected net sales", f"€{total_sales:,.0f}", metric_key="Net sales")
    with k2:
        render_kpi_card(
            "Selected return rate",
            f"{global_return_rate:.1%}" if global_return_rate is not None else "—",
            metric_key="Return rate",
        )
    with k3:
        render_kpi_card(
            "Selected margin",
            f"{global_margin_pct:.1%}" if global_margin_pct is not None else "—",
            metric_key="Margin %",
        )
    with k4:
        render_kpi_card(
            "Top country",
            top_country.iloc[0]["country_name"] if not top_country.empty else "—",
            metric_key="Top country",
        )
    with k5:
        render_kpi_card(
            "Top category",
            top_category.iloc[0]["category"] if not top_category.empty else "—",
            metric_key="Top wholesale category",
        )

    title_prefix = "All channels"
    chart_panel(
        f"{title_prefix} map · {metric_label}",
        "Map metric",
        build_world_map_heatmap(filtered_global, metric=map_metric),
        guide_key="Map metric",
        chart_key="global_map",
    )
    left, right = st.columns(2)
    with left:
        chart_panel(
            f"Top countries · {metric_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_country_bar_chart(
                filtered_global,
                metric=map_metric,
                stack_by_channel=True,
            ),
            guide_key="Country bar",
            chart_key="global_country_bar",
        )
    with right:
        chart_panel(
            f"Top categories · {metric_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_wholesale_category_bar(
                filtered_global,
                metric=map_metric,
                title_prefix=title_prefix,
                stack_by_channel=True,
            ),
            guide_key="Wholesale category bar",
            chart_key="global_category_bar",
        )

    row2_left, row2_right = st.columns(2)
    with row2_left:
        chart_panel(
            f"Country × category · {metric_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_wholesale_country_category_heatmap(
                filtered_global,
                metric=map_metric,
                title_prefix=title_prefix,
            ),
            guide_key="Wholesale country × category",
            chart_key="global_country_category_heatmap",
        )
    with row2_right:
        chart_panel(
            f"Category trend · {metric_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_wholesale_category_trend(
                filtered_global,
                metric=map_metric,
                title_prefix=title_prefix,
            ),
            guide_key="Wholesale category trend",
            chart_key="global_category_trend",
        )

    chart_panel(
        "Channel comparison · Margin % vs return rate",
        "Margin %",
        build_channel_rate_comparison(filtered_global),
        guide_key="Channel rate comparison",
        chart_key="global_channel_rate_comparison",
    )

    if len(selected_view_channels) > 1:
        chart_panel(
            f"Country × channel × category · {metric_label}",
            MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
            build_country_channel_category_heatmap(filtered_global, metric=map_metric),
            guide_key="Country heatmap",
            chart_key="global_country_channel_category_heatmap",
        )

    summary = summary.sort_values("net_sales", ascending=False).head(30)
    st.markdown("**Top country × channel × category combinations**")
    st.dataframe(
        summary.assign(
            net_sales=lambda d: d["net_sales"].map(lambda v: f"€{v:,.0f}"),
            return_rate=lambda d: d["return_rate"].map(lambda v: f"{v:.1%}"),
            margin_pct=lambda d: d["margin_pct"].map(lambda v: f"{v:.1%}"),
        )[["country_name", "channel", "category", "net_sales", "return_rate", "margin_pct"]],
        use_container_width=True,
        hide_index=True,
    )
    all_channel_pos, all_channel_neg, all_channel_neu = build_all_channel_category_insights(
        filtered_global,
        map_metric=map_metric,
    )
    render_insights_footer(
        "All-channel insights",
        all_channel_pos,
        all_channel_neg,
        all_channel_neu,
    )


def render_channel_legend(channels) -> None:
    colors = channel_color_map(channels)
    chips = " ".join(
        f'<span style="display:inline-block;margin:0 .35rem .35rem 0;padding:.2rem .55rem;'
        f'border-radius:999px;background:{colors[ch]}22;color:{colors[ch]};'
        f'border:1px solid {colors[ch]}66;font-size:.78rem;font-weight:600;">{ch}</span>'
        for ch in colors
    )
    st.markdown(chips, unsafe_allow_html=True)


def _emphasis_html(text: str) -> str:
    parts = text.split("**")
    rendered = []
    for index, part in enumerate(parts):
        if index % 2 == 1:
            rendered.append(f"<strong>{part}</strong>")
        else:
            rendered.append(part)
    return "".join(rendered)


def kpi_delta(pct: float | None) -> tuple[str, str]:
    formatted = format_yoy_delta(pct)
    if formatted is None:
        return "No prior-period data", "neutral"
    if pct is None or pct == 0:
        return formatted, "neutral"
    return formatted, "up" if pct > 0 else "down"


DELTA_TONE_COLORS = {
    "up": GOOD,
    "down": BAD,
    "neutral": "#64748b",
}


def _delta_tone_from_text(delta: str) -> str:
    stripped = delta.strip()
    if stripped.startswith("+"):
        return "up"
    if stripped.startswith("-"):
        return "down"
    return "neutral"


def render_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    tone: str = "neutral",
    metric_key: str = "",
    extra_detail: str = "",
) -> None:
    definition = METRIC_TOOLTIPS.get(metric_key, "")
    details = KPI_DETAILS.get(metric_key, "")
    if extra_detail:
        details = f"{details} {extra_detail}".strip()
    tip = _info_tooltip_html(definition=definition, details=details)
    if delta is not None:
        resolved_tone = tone if tone != "neutral" else _delta_tone_from_text(delta)
        delta_color = DELTA_TONE_COLORS.get(resolved_tone, DELTA_TONE_COLORS["neutral"])
        delta_html = (
            f'<span class="kpi-card-delta" style="color:{delta_color};">'
            f"{html.escape(delta)}</span>"
        )
    else:
        delta_html = '<span class="kpi-card-delta kpi-card-delta-empty" aria-hidden="true">&nbsp;</span>'
    card_class = "kpi-card kpi-card-period" if metric_key == "Period" else "kpi-card"
    with st.container(border=True):
        st.markdown(
            f'<div class="{card_class}">'
            f'<div class="kpi-card-top">'
            f'<span class="kpi-card-label">{html.escape(label)}</span>'
            f"{tip}"
            f"</div>"
            f'<span class="kpi-card-value">{html.escape(value)}</span>'
            f"{delta_html}"
            f"</div>",
            unsafe_allow_html=True,
        )


def _insight_box_html(
    heading: str,
    items: list[str],
    css_class: str,
    fallback: str,
) -> str:
    bullets = items or [fallback]
    list_items = "".join(f"<li>{_emphasis_html(item)}</li>" for item in bullets)
    return (
        f'<div class="insight-box {css_class}">'
        f"<h5>{heading}</h5>"
        f"<ul>{list_items}</ul>"
        f"</div>"
    )


def render_insights_footer(
    title: str,
    positive: list[str],
    negative: list[str],
    neutral: list[str],
) -> None:
    st.markdown('<div class="insight-footer">', unsafe_allow_html=True)
    st.markdown(f"#### {title}")
    st.markdown('<div id="insight-row-marker"></div>', unsafe_allow_html=True)
    sections = [
        ("Strengths", positive, "insight-positive", "No clear positive signals in this slice."),
        ("Risks", negative, "insight-negative", "No major risk flags in this slice."),
        ("Context", neutral, "insight-neutral", "Adjust filters to explore other views."),
    ]
    columns = st.columns(3)
    for column, (heading, items, css_class, fallback) in zip(columns, sections):
        with column:
            st.markdown(_insight_box_html(heading, items, css_class, fallback), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


@st.cache_data(ttl=600)
def get_wholesale_data(_schema_version: int = 5):
    return load_wholesale_performance()


@st.cache_data(ttl=600)
def get_category_country_channel_data(_schema_version: int = 6):
    return load_category_country_channel_performance()


@st.cache_data(ttl=600)
def get_data_quality_summary(_schema_version: int = 5):
    return load_data_quality_summary()


@st.cache_data(ttl=600)
def get_data_quality_detail(issue_type: str, limit: int = 100, _schema_version: int = 5):
    return load_data_quality_detail(issue_type, limit=limit)


@st.cache_data(ttl=600)
def get_channel_data(granularity: str = "month", _schema_version: int = 5):
    return load_channel_performance(granularity)


@st.cache_data(ttl=600)
def get_country_data(granularity: str = "month", _schema_version: int = 5):
    return load_country_performance(granularity)


st.set_page_config(page_title="Channel Performance | Alohas", page_icon="📊", layout="wide")
st.markdown(STREAMLIT_CSS, unsafe_allow_html=True)
st.markdown(
    """
    <div class="dashboard-header">
      <h1>Channel Performance</h1>
      <p>How is the business performing across channels and countries?</p>
    </div>
    """,
    unsafe_allow_html=True,
)


try:
    df_meta = get_channel_data("month")
    country_meta = get_country_data("month")
    wholesale_meta = get_wholesale_data()
    category_country_channel_meta = get_category_country_channel_data()
except Exception as exc:
    st.error("Could not load dashboard data.")
    st.code(str(exc))
    st.caption(
        "For Streamlit Cloud without GCP: set env `DASHBOARD_DATA_SOURCE=cache` "
        "and commit `dashboard/cache/*.parquet` (run `python dashboard/export_cache.py` locally)."
    )
    st.exception(exc)
    st.stop()

if "period_preset" not in st.session_state:
    st.session_state["period_preset"] = "last_1_year"

active_granularity = preset_granularity(
    st.session_state["period_preset"]
    if st.session_state["period_preset"] in PERIOD_PRESETS
    else "last_1_year"
)

try:
    df = get_channel_data(active_granularity)
    country_df = get_country_data("month")
    wholesale_df = get_wholesale_data()
    category_country_channel_df = get_category_country_channel_data()
except Exception as exc:
    st.error("Could not load dashboard data.")
    st.code(str(exc))
    st.caption(
        "For Streamlit Cloud without GCP: set env `DASHBOARD_DATA_SOURCE=cache` "
        "and commit `dashboard/cache/*.parquet` (run `python dashboard/export_cache.py` locally)."
    )
    st.exception(exc)
    st.stop()

min_date, max_date = picker_date_bounds(df, country_df)
channel_min_date, channel_max_date = data_bounds(df_meta)
country_min_date, country_max_date = data_bounds(country_meta)
wholesale_min_date, wholesale_max_date = data_bounds(wholesale_meta)
wholesale_categories = sorted(wholesale_meta["category"].dropna().unique())
channels = sorted(df_meta["channel"].unique())
countries = sorted(country_meta["country"].unique())

if "period" not in st.session_state:
    st.session_state["period"] = period_for_preset(
        st.session_state["period_preset"],
        df,
        country_df,
        bounds_min=min_date,
        bounds_max=max_date,
    )

st.session_state["period"] = clamp_period(
    *st.session_state["period"],
    min_date,
    max_date,
)

with st.sidebar:
    st.markdown("### Filters")
    st.caption(f"Analytics source: `{analytics_data_source_label()}`")
    selected_channels = st.multiselect("Channel", channels, default=channels)
    selected_countries = st.multiselect(
        "Country",
        countries,
        default=countries,
        format_func=lambda code: country_df.loc[country_df["country"] == code, "country_name"].iloc[0],
    )
    st.markdown("**Compare period**")
    preset_keys = list(PERIOD_PRESETS.keys())
    row_one = st.columns(3)
    row_two = st.columns(2)
    for column, preset_key in zip(row_one + row_two, preset_keys):
        preset_label = PERIOD_PRESETS[preset_key]
        with column:
            is_active = st.session_state["period_preset"] == preset_key
            if st.button(
                preset_label,
                key=f"preset_{preset_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["period_preset"] = preset_key
                preset_gran = preset_granularity(preset_key)
                preset_channel = get_channel_data(preset_gran)
                preset_country = get_country_data(preset_gran)
                preset_min, preset_max = picker_date_bounds(preset_channel, preset_country)
                st.session_state["period"] = period_for_preset(
                    preset_key,
                    preset_channel,
                    preset_country,
                    bounds_min=preset_min,
                    bounds_max=preset_max,
                )
                st.rerun()
    granularity_labels = {
        "day": "Charts use **daily** granularity.",
        "week": "Charts use **weekly** granularity.",
        "month": "Charts use **monthly** granularity.",
    }
    preset = st.session_state.get("period_preset", "last_1_year")
    if preset == "last_month":
        gran_caption = "Last month is shown in **weekly** buckets."
    elif preset == "weekly":
        gran_caption = "Charts use the last **8 weeks** at weekly granularity."
    else:
        gran_caption = granularity_labels[active_granularity]
    st.caption(
        f"{gran_caption} "
        "YoY deltas compare the same range **one year earlier**."
    )
    if st.button("Use full data range", use_container_width=True):
        st.session_state["period_preset"] = "custom"
        st.session_state["period"] = clamp_period(
            channel_min_date,
            country_max_date,
            min_date,
            max_date,
        )
        st.rerun()
    st.caption(
        f"Data available **{format_period_label(channel_min_date, channel_max_date)}**."
    )
    date_range = st.date_input(
        "Custom range",
        value=st.session_state["period"],
        min_value=min_date,
        max_value=max_date,
        help="Override the preset with a custom start/end date. "
        f"Data runs through {country_max_date.strftime('%b %Y')}.",
        key="period_filter",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        if date_range != st.session_state["period"]:
            st.session_state["period"] = date_range
            matched = match_period_preset(
                date_range[0],
                date_range[1],
                df,
                country_df,
                bounds_min=min_date,
                bounds_max=max_date,
                granularity=active_granularity,
            )
            st.session_state["period_preset"] = matched or "custom"
    with st.expander("Metric definitions"):
        for name, desc in METRIC_TOOLTIPS.items():
            st.markdown(f"**{name}** — {desc}")
    if st.button("Clear cache & refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

start_date, end_date = parse_date_range(date_range, min_date, max_date)

if not selected_channels:
    st.warning("Select at least one channel.")
    st.stop()
if not selected_countries:
    st.warning("Select at least one country.")
    st.stop()

filtered = filter_data(df, selected_channels, start_date, end_date)

country_overlap = intersect_period(start_date, end_date, country_min_date, country_max_date)
country_period_label = (
    f"{country_overlap[0].strftime('%b %Y')} – {country_overlap[1].strftime('%b %Y')}"
    if country_overlap
    else f"{country_min_date.strftime('%b %Y')} – {country_max_date.strftime('%b %Y')}"
)

if country_overlap:
    c_start, c_end = country_overlap
    filtered_countries = filter_data(
        country_df, selected_channels, c_start, c_end, countries=selected_countries,
    )
    country_source_label = None
else:
    filtered_countries = filter_data(
        country_df,
        selected_channels,
        country_min_date,
        country_max_date,
        countries=selected_countries,
    )
    country_source_label = country_period_label

country_kpi_start = country_overlap[0] if country_overlap else country_min_date
country_kpi_end = country_overlap[1] if country_overlap else country_max_date
country_kpis = compute_country_kpi(
    country_df,
    selected_channels,
    country_kpi_start,
    country_kpi_end,
    countries=selected_countries,
)

if filtered.empty:
    st.warning("No data for the selected period or filters. Try a wider date range.")
    st.stop()

channel_kpis = compute_channel_kpis(df, selected_channels, start_date, end_date)
latest = channel_kpis["latest_month"] or latest_period(filtered)
period_col = resolve_period_col(filtered)
prior_slice = filtered[filtered[period_col] == prior_year_period(latest)]

if not country_overlap:
    st.info(
        f"Country breakdown is only available **{country_min_date.strftime('%b %Y')} – "
        f"{country_max_date.strftime('%b %Y')}**. Channel KPIs use your selected period; "
        f"country views show the latest available country data."
    )

c1, c2, c3, c4, c5 = st.columns(5)
period_delta = (
    f"vs {channel_kpis['prior_period_label']}"
    if channel_kpis["has_prior_period"]
    else "No prior-period data"
)
with c1:
    render_kpi_card(
        "Period",
        channel_kpis["period_label"],
        period_delta,
        tone="neutral",
        metric_key="Period",
    )
with c2:
    sales_delta, sales_tone = kpi_delta(channel_kpis["net_sales_yoy"])
    render_kpi_card(
        "Net sales",
        f"€{channel_kpis['net_sales']:,.0f}",
        sales_delta,
        tone=sales_tone,
        metric_key="Net sales",
    )
with c3:
    return_rate = channel_kpis["return_rate"]
    return_value = f"{return_rate:.1%}" if return_rate is not None else "—"
    return_delta, return_tone = kpi_delta(channel_kpis["return_rate_yoy"])
    render_kpi_card(
        "Avg return rate",
        return_value,
        return_delta,
        tone=return_tone,
        metric_key="Avg return rate",
    )
with c4:
    render_kpi_card(
        "Top channel",
        channel_kpis["top_channel"].title(),
        metric_key="Top channel",
    )
with c5:
    render_kpi_card(
        "Top country",
        country_kpis["top_country"],
        metric_key="Top country",
        extra_detail=f"Country period: {country_kpis['period_label']}.",
    )

render_channel_legend(selected_channels)

case_wholesale = filter_wholesale_data(
    wholesale_df,
    start_date=start_date,
    end_date=end_date,
    countries=selected_countries,
)
wholesale_kpis = compute_wholesale_kpis(
    wholesale_df,
    start_date,
    end_date,
    countries=selected_countries,
)

tab_channels, tab_countries, tab_q1, tab_q2, tab_q3, tab_table, tab_quality = st.tabs(
    [
        "Channel scorecard",
        "Countries & wholesale",
        "01 · Channel sales",
        "02 · Returns",
        "03 · Margin",
        "Data tables",
        "Data quality",
    ],
)

with tab_channels:
    left, right = st.columns(2)
    with left:
        chart_panel("Net sales", "Net sales", build_net_sales_chart(filtered), chart_key="scorecard_net_sales")
        chart_panel("Return rate", "Return rate", build_return_rate_chart(filtered), chart_key="scorecard_return_rate")
    with right:
        chart_panel("Channel mix", "Mix %", build_mix_chart(filtered), chart_key="scorecard_mix")
        chart_panel("Contribution margin", "Margin %", build_margin_chart(filtered), chart_key="scorecard_margin")

    channel_pos, channel_neg, channel_neu = build_channel_insights(filtered, latest, prior_slice)
    render_insights_footer(
        "Channel insights",
        channel_pos,
        channel_neg,
        channel_neu,
    )

with tab_countries:
    map_metric = st.selectbox(
        "Map metric",
        options=list(MAP_METRIC_OPTIONS.keys()),
        format_func=lambda key: MAP_METRIC_OPTIONS[key],
        key="countries_map_metric",
    )
    country_tabs = st.tabs([
        "All channels",
        "Wholesale · category",
        "All channels · country × category",
    ])
    tab_all_countries = country_tabs[0]
    tab_wholesale = country_tabs[1]
    tab_global_category = country_tabs[2]

    with tab_all_countries:
        if filtered_countries.empty:
            st.warning("No country rows for the selected channel and country filters.")
        else:
            if country_source_label:
                st.caption(f"Showing country data for **{country_source_label}**.")
            map_label = MAP_METRIC_OPTIONS.get(map_metric, map_metric)
            chart_panel(
                f"World map · {map_label}",
                "Map metric",
                build_world_map_heatmap(filtered_countries, metric=map_metric),
                guide_key="Map metric",
                chart_key="countries_map",
            )
            left, right = st.columns(2)
            with left:
                chart_panel(
                    f"Top countries · {map_label}",
                    MAP_METRIC_OPTIONS.get(map_metric, "Net sales"),
                    build_country_bar_chart(
                        filtered_countries,
                        metric=map_metric,
                        stack_by_channel=True,
                    ),
                    guide_key="Country bar",
                    chart_key="countries_bar",
                )
            with right:
                chart_panel(
                    "Country × channel",
                    "Net sales",
                    build_country_channel_heatmap(filtered_countries),
                    guide_key="Country heatmap",
                    chart_key="countries_channel_heatmap",
                )
            render_data_table(
                filtered_countries,
                by_country=True,
                title="Country detail table",
                metric_key="Net sales",
                guide_key="Country table",
            )

            country_pos, country_neg, country_neu = build_country_insights(
                filtered_countries,
                map_metric=map_metric,
            )
            render_insights_footer(
                "Country insights",
                country_pos,
                country_neg,
                country_neu,
            )

    with tab_wholesale:
        render_wholesale_dashboard(
            wholesale_df,
            start_date=start_date,
            end_date=end_date,
            selected_countries=selected_countries,
            map_metric=map_metric,
        )

    with tab_global_category:
        render_global_country_channel_category(
            category_country_channel_df,
            wholesale_df,
            start_date=country_kpi_start,
            end_date=country_kpi_end,
            selected_channels=selected_channels,
            selected_countries=selected_countries,
            map_metric=map_metric,
        )

with tab_q1:
    render_q1_channel_page(filtered, case_wholesale, channel_kpis, wholesale_kpis)

with tab_q2:
    render_q2_returns_page()

with tab_q3:
    render_q3_margin_page(filtered, case_wholesale, filtered_countries)

with tab_table:
    render_data_table(
        filtered,
        by_country=False,
        title="By channel",
        metric_key="Channel",
        guide_key="Channel table",
    )
    render_data_table(
        filtered_countries,
        by_country=True,
        title="By country",
        metric_key="Net sales",
        guide_key="Country table",
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "Download channel CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="channel_performance.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "Download country CSV",
            data=filtered_countries.to_csv(index=False).encode("utf-8"),
            file_name="channel_country_performance.csv",
            mime="text/csv",
            use_container_width=True,
        )

with tab_quality:
    render_data_quality_tab()
