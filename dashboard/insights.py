"""Auto-generated dashboard insights from filtered performance data."""

from __future__ import annotations

import pandas as pd

from data import (
    MAP_METRIC_OPTIONS,
    latest_period,
    prior_year_period,
    resolve_period_col,
    yoy_pct,
)


def _metric_label(metric: str) -> str:
    return MAP_METRIC_OPTIONS.get(metric, metric.replace("_", " "))


def _format_metric_value(metric: str, value: float) -> str:
    if metric in ("net_sales", "contribution_margin"):
        return f"€{value:,.0f}"
    if metric == "quantity_sold":
        return f"{value:,.0f} units"
    if metric in ("return_rate", "contribution_margin_pct"):
        return f"{value:.1%}"
    return f"{value:,.0f}"


def _higher_is_better(metric: str) -> bool:
    return metric != "return_rate"


def _country_totals_df(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("country_name", as_index=False).agg(
        net_sales=("net_sales", "sum"),
        quantity_sold=("quantity_sold", "sum"),
        quantity_returned=("quantity_returned", "sum"),
        contribution_margin=("contribution_margin", "sum"),
    )
    grouped["return_rate"] = grouped["quantity_returned"] / grouped["quantity_sold"]
    grouped["contribution_margin_pct"] = (
        grouped["contribution_margin"] / grouped["net_sales"]
    )
    return grouped


def _country_channel_totals_df(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(["country_name", "channel"], as_index=False).agg(
        net_sales=("net_sales", "sum"),
        quantity_sold=("quantity_sold", "sum"),
        quantity_returned=("quantity_returned", "sum"),
        contribution_margin=("contribution_margin", "sum"),
    )
    grouped["return_rate"] = grouped["quantity_returned"] / grouped["quantity_sold"]
    grouped["contribution_margin_pct"] = (
        grouped["contribution_margin"] / grouped["net_sales"]
    )
    return grouped


def _wholesale_country_totals_df(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("country_name", as_index=False).agg(
        net_sales=("net_sales", "sum"),
        quantity_sold=("quantity_sold", "sum"),
        quantity_returned=("quantity_returned", "sum"),
        contribution_margin=("contribution_margin", "sum"),
    )
    grouped["return_rate"] = grouped["quantity_returned"] / grouped["quantity_sold"]
    grouped["contribution_margin_pct"] = (
        grouped["contribution_margin"] / grouped["net_sales"]
    )
    return grouped


def _wholesale_category_totals_df(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("category", as_index=False).agg(
        net_sales=("net_sales", "sum"),
        quantity_sold=("quantity_sold", "sum"),
        quantity_returned=("quantity_returned", "sum"),
        contribution_margin=("contribution_margin", "sum"),
    )
    grouped["return_rate"] = grouped["quantity_returned"] / grouped["quantity_sold"]
    grouped["contribution_margin_pct"] = (
        grouped["contribution_margin"] / grouped["net_sales"]
    )
    return grouped


def _format_period_point(value: pd.Timestamp, period_col: str) -> str:
    if period_col == "period_day":
        return value.strftime("%d %b %Y")
    if period_col == "period_week":
        return f"week of {value.strftime('%d %b %Y')}"
    return value.strftime("%b %Y")


def _cap(items: list[str], limit: int = 3) -> list[str]:
    return items[:limit]


def build_channel_insights(
    df: pd.DataFrame,
    latest: pd.Timestamp,
    prior_slice: pd.DataFrame,
) -> tuple[list[str], list[str], list[str]]:
    positives: list[str] = []
    negatives: list[str] = []
    neutrals: list[str] = []

    if df.empty:
        return positives, negatives, neutrals

    period_col = resolve_period_col(df)
    latest_slice = df[df[period_col] == latest]
    if latest_slice.empty:
        return positives, negatives, neutrals

    period_label = _format_period_point(latest, period_col)

    total_latest = latest_slice["net_sales"].sum()
    total_prior = prior_slice["net_sales"].sum() if not prior_slice.empty else None
    total_yoy = yoy_pct(total_latest, total_prior) if total_prior is not None else None

    if total_yoy is not None:
        if total_yoy >= 0.05:
            positives.append(
                f"Portfolio net sales grew **{total_yoy:.1%}** in {period_label} vs last year."
            )
        elif total_yoy <= -0.05:
            negatives.append(
                f"Portfolio net sales fell **{abs(total_yoy):.1%}** in {period_label} vs last year."
            )
        else:
            neutrals.append(
                f"Portfolio net sales is broadly flat (**{total_yoy:+.1%}** YoY) in {period_label}."
            )

    if "net_sales_yoy_pct" in latest_slice.columns:
        yoy_rows = latest_slice.dropna(subset=["net_sales_yoy_pct"])
        if not yoy_rows.empty:
            best = yoy_rows.loc[yoy_rows["net_sales_yoy_pct"].idxmax()]
            if best["net_sales_yoy_pct"] > 0:
                positives.append(
                    f"**{best['channel'].title()}** leads channel growth at "
                    f"**{best['net_sales_yoy_pct']:+.1%}** net sales YoY."
                )
            worst = yoy_rows.loc[yoy_rows["net_sales_yoy_pct"].idxmin()]
            if worst["net_sales_yoy_pct"] < -0.05:
                negatives.append(
                    f"**{worst['channel'].title()}** is the weakest channel at "
                    f"**{worst['net_sales_yoy_pct']:+.1%}** net sales YoY."
                )

    best_margin = latest_slice.loc[latest_slice["contribution_margin_pct"].idxmax()]
    positives.append(
        f"**{best_margin['channel'].title()}** delivers the highest margin "
        f"(**{best_margin['contribution_margin_pct']:.1%}**) in the latest month."
    )

    lowest_return = latest_slice.loc[latest_slice["return_rate"].idxmin()]
    positives.append(
        f"**{lowest_return['channel'].title()}** keeps the lowest return rate "
        f"(**{lowest_return['return_rate']:.1%}**)."
    )

    highest_return = latest_slice.loc[latest_slice["return_rate"].idxmax()]
    if highest_return["return_rate"] >= 0.12:
        negatives.append(
            f"**{highest_return['channel'].title()}** has the highest return rate "
            f"(**{highest_return['return_rate']:.1%}**) — worth monitoring."
        )

    if "contribution_margin_pct_yoy_pp" in latest_slice.columns:
        margin_yoy = latest_slice.dropna(subset=["contribution_margin_pct_yoy_pp"])
        if not margin_yoy.empty:
            compressed = margin_yoy.loc[margin_yoy["contribution_margin_pct_yoy_pp"].idxmin()]
            if compressed["contribution_margin_pct_yoy_pp"] < -0.02:
                negatives.append(
                    f"**{compressed['channel'].title()}** margin compressed "
                    f"**{compressed['contribution_margin_pct_yoy_pp']:.1f} pp** YoY."
                )

    top_mix = latest_slice.loc[latest_slice["pct_of_total_net_sales"].idxmax()]
    neutrals.append(
        f"**{top_mix['channel'].title()}** represents **{top_mix['pct_of_total_net_sales']:.0%}** "
        f"of net sales mix in {period_label}."
    )

    period_sales = df.groupby("channel", as_index=False)["net_sales"].sum()
    period_sales = period_sales.sort_values("net_sales", ascending=False)
    top_period = period_sales.iloc[0]
    neutrals.append(
        f"**{top_period['channel'].title()}** generated **€{top_period['net_sales']:,.0f}** "
        f"over the selected period — the largest channel by revenue."
    )

    periods = df[period_col].nunique()
    unit = {"period_day": "days", "period_week": "weeks", "period_month": "months"}[period_col]
    neutrals.append(
        f"The view spans **{periods} {unit}** and **{df['channel'].nunique()} channels** "
        f"in the current filter selection."
    )

    return _cap(positives), _cap(negatives), _cap(neutrals)


def build_country_insights(
    df: pd.DataFrame,
    map_metric: str = "net_sales",
) -> tuple[list[str], list[str], list[str]]:
    positives: list[str] = []
    negatives: list[str] = []
    neutrals: list[str] = []

    if df.empty:
        return positives, negatives, neutrals

    latest = latest_period(df)
    if latest is None:
        return positives, negatives, neutrals

    period_col = resolve_period_col(df)
    latest_slice = df[df[period_col] == latest]
    prior_point = prior_year_period(latest)
    prior_slice = df[df[period_col] == prior_point]
    period_label = _format_period_point(latest, period_col)
    metric_label = _metric_label(map_metric)
    higher_better = _higher_is_better(map_metric)

    country_period = _country_totals_df(df)
    country_latest = _country_totals_df(latest_slice) if not latest_slice.empty else country_period.iloc[0:0]

    ranked = country_period.sort_values(map_metric, ascending=not higher_better)
    if ranked.empty or ranked[map_metric].isna().all():
        return positives, negatives, neutrals

    top_country = ranked.iloc[0]
    bottom_country = ranked.iloc[-1]

    if map_metric == "return_rate":
        positives.append(
            f"**{top_country['country_name']}** has the lowest **{metric_label}** "
            f"(**{_format_metric_value(map_metric, top_country[map_metric])}**) in the period."
        )
        if bottom_country["return_rate"] >= 0.12:
            negatives.append(
                f"**{bottom_country['country_name']}** has the highest **{metric_label}** "
                f"(**{_format_metric_value(map_metric, bottom_country[map_metric])}**) "
                f"in {period_label}."
            )
    else:
        positives.append(
            f"**{top_country['country_name']}** leads the period on **{metric_label}** with "
            f"**{_format_metric_value(map_metric, top_country[map_metric])}**."
        )
        if map_metric == "contribution_margin_pct" and len(ranked) >= 2:
            spread = top_country[map_metric] - bottom_country[map_metric]
            if spread >= 0.05:
                negatives.append(
                    f"**{bottom_country['country_name']}** lags on **{metric_label}** at "
                    f"**{_format_metric_value(map_metric, bottom_country[map_metric])}**."
                )

    if not country_latest.empty and map_metric != "return_rate":
        best_return = country_latest.loc[country_latest["return_rate"].idxmin()]
        positives.append(
            f"**{best_return['country_name']}** has the lowest return rate "
            f"(**{best_return['return_rate']:.1%}**) in {period_label}."
        )
        worst_return = country_latest.loc[country_latest["return_rate"].idxmax()]
        if worst_return["return_rate"] >= 0.12:
            negatives.append(
                f"**{worst_return['country_name']}** has the highest return rate "
                f"(**{worst_return['return_rate']:.1%}**) in {period_label}."
            )

    if not prior_slice.empty and not country_latest.empty:
        current_totals = _country_totals_df(latest_slice)
        prior_totals = _country_totals_df(prior_slice)
        merged = current_totals.merge(
            prior_totals,
            on="country_name",
            how="inner",
            suffixes=("_current", "_prior"),
        )
        if not merged.empty:
            current_col = f"{map_metric}_current"
            prior_col = f"{map_metric}_prior"
            merged["yoy"] = merged.apply(
                lambda row: yoy_pct(row[current_col], row[prior_col]),
                axis=1,
            )
            merged = merged.dropna(subset=["yoy"])
            if not merged.empty:
                if higher_better:
                    decliner = merged.loc[merged["yoy"].idxmin()]
                    if decliner["yoy"] < -0.05:
                        negatives.append(
                            f"**{decliner['country_name']}** **{metric_label}** declined "
                            f"**{decliner['yoy']:+.1%}** YoY in {period_label}."
                        )
                    gainer = merged.loc[merged["yoy"].idxmax()]
                    if gainer["yoy"] > 0.05 and len(positives) < 3:
                        positives.append(
                            f"**{gainer['country_name']}** is the fastest-growing market on "
                            f"**{metric_label}** at **{gainer['yoy']:+.1%}** YoY in {period_label}."
                        )
                else:
                    improver = merged.loc[merged["yoy"].idxmin()]
                    if improver["yoy"] < -0.05:
                        positives.append(
                            f"**{improver['country_name']}** improved **{metric_label}** "
                            f"**{improver['yoy']:+.1%}** YoY in {period_label}."
                        )
                    worsener = merged.loc[merged["yoy"].idxmax()]
                    if worsener["yoy"] > 0.05:
                        negatives.append(
                            f"**{worsener['country_name']}** **{metric_label}** rose "
                            f"**{worsener['yoy']:+.1%}** YoY in {period_label}."
                        )

    metric_total = country_period[map_metric].sum()
    if len(country_period) >= 2 and metric_total:
        share_top = top_country[map_metric] / metric_total
        neutrals.append(
            f"**{top_country['country_name']}** concentrates **{share_top:.0%}** of "
            f"country **{metric_label.lower()}** in the selected period."
        )

    channel_country = _country_channel_totals_df(df).sort_values(
        map_metric, ascending=not higher_better
    )
    if not channel_country.empty:
        top_pair = channel_country.iloc[0]
        neutrals.append(
            f"The strongest **country × channel** pair on **{metric_label}** is "
            f"**{top_pair['country_name']} · {top_pair['channel'].title()}** "
            f"({_format_metric_value(map_metric, top_pair[map_metric])})."
        )

    unit = {"period_day": "days", "period_week": "weeks", "period_month": "months"}[period_col]
    neutrals.append(
        f"Geographic view covers **{df['country_name'].nunique()} countries** and "
        f"**{df['channel'].nunique()} channels** across **{df[period_col].nunique()} {unit}** "
        f"· map metric: **{metric_label}**."
    )

    return _cap(positives), _cap(negatives), _cap(neutrals)


def build_wholesale_insights(
    df: pd.DataFrame,
    map_metric: str = "net_sales",
) -> tuple[list[str], list[str], list[str]]:
    positives: list[str] = []
    negatives: list[str] = []
    neutrals: list[str] = []

    if df.empty:
        return positives, negatives, neutrals

    latest = latest_period(df)
    if latest is None:
        return positives, negatives, neutrals

    period_col = "period_month"
    latest_slice = df[df[period_col] == latest]
    prior_point = prior_year_period(latest)
    prior_slice = df[df[period_col] == prior_point]
    period_label = _format_period_point(latest, period_col)
    metric_label = _metric_label(map_metric)
    higher_better = _higher_is_better(map_metric)

    country_period = _wholesale_country_totals_df(df)
    category_period = _wholesale_category_totals_df(df)

    country_ranked = country_period.sort_values(map_metric, ascending=not higher_better)
    category_ranked = category_period.sort_values(map_metric, ascending=not higher_better)

    if country_ranked.empty or country_ranked[map_metric].isna().all():
        return positives, negatives, neutrals

    top_country = country_ranked.iloc[0]
    bottom_country = country_ranked.iloc[-1]
    metric_total = country_period[map_metric].sum()

    if map_metric == "return_rate":
        positives.append(
            f"**{top_country['country_name']}** has the lowest wholesale **{metric_label}** "
            f"(**{_format_metric_value(map_metric, top_country[map_metric])}**)."
        )
        if bottom_country["return_rate"] >= 0.08:
            negatives.append(
                f"**{bottom_country['country_name']}** has the highest wholesale **{metric_label}** "
                f"(**{_format_metric_value(map_metric, bottom_country[map_metric])}**)."
            )
    else:
        share = top_country[map_metric] / metric_total if metric_total else 0
        positives.append(
            f"**{top_country['country_name']}** leads wholesale **{metric_label}** with "
            f"**{_format_metric_value(map_metric, top_country[map_metric])}** "
            f"(**{share:.0%}** of total)."
        )

    if not category_ranked.empty:
        top_category = category_ranked.iloc[0]
        positives.append(
            f"**{top_category['category']}** is the top wholesale category on **{metric_label}** "
            f"({_format_metric_value(map_metric, top_category[map_metric])})."
        )

    if map_metric != "return_rate" and map_metric != "contribution_margin_pct":
        best_margin = country_period.loc[country_period["contribution_margin_pct"].idxmax()]
        positives.append(
            f"**{best_margin['country_name']}** has the strongest wholesale margin "
            f"(**{best_margin['contribution_margin_pct']:.1%}**)."
        )
    elif map_metric == "contribution_margin_pct" and len(country_ranked) >= 2:
        spread = top_country[map_metric] - bottom_country[map_metric]
        if spread >= 0.03:
            negatives.append(
                f"**{bottom_country['country_name']}** trails on wholesale **{metric_label}** at "
                f"**{_format_metric_value(map_metric, bottom_country[map_metric])}**."
            )

    if map_metric != "return_rate":
        worst_return = country_period.loc[country_period["return_rate"].idxmax()]
        if worst_return["return_rate"] >= 0.08:
            negatives.append(
                f"**{worst_return['country_name']}** has the highest wholesale return rate "
                f"(**{worst_return['return_rate']:.1%}**)."
            )

    if not prior_slice.empty and not latest_slice.empty:
        current_totals = _wholesale_country_totals_df(latest_slice)
        prior_totals = _wholesale_country_totals_df(prior_slice)
        merged = current_totals.merge(
            prior_totals,
            on="country_name",
            how="inner",
            suffixes=("_current", "_prior"),
        )
        if not merged.empty:
            current_col = f"{map_metric}_current"
            prior_col = f"{map_metric}_prior"
            merged["yoy"] = merged.apply(
                lambda row: yoy_pct(row[current_col], row[prior_col]),
                axis=1,
            )
            merged = merged.dropna(subset=["yoy"])
            if not merged.empty:
                if higher_better:
                    decliner = merged.loc[merged["yoy"].idxmin()]
                    if decliner["yoy"] < -0.05:
                        negatives.append(
                            f"**{decliner['country_name']}** wholesale **{metric_label}** fell "
                            f"**{decliner['yoy']:+.1%}** YoY in {period_label}."
                        )
                else:
                    worsener = merged.loc[merged["yoy"].idxmax()]
                    if worsener["yoy"] > 0.05:
                        negatives.append(
                            f"**{worsener['country_name']}** wholesale **{metric_label}** rose "
                            f"**{worsener['yoy']:+.1%}** YoY in {period_label}."
                        )

    if len(country_period) >= 2 and metric_total:
        share_top = top_country[map_metric] / metric_total
        if share_top >= 0.35:
            neutrals.append(
                f"Wholesale **{metric_label.lower()}** is **concentrated**: top country holds "
                f"**{share_top:.0%}**."
            )

    neutrals.append(
        f"Wholesale view spans **{df['country_name'].nunique()} countries**, "
        f"**{df['category'].nunique()} categories**, "
        f"**{df[period_col].nunique()} months** · map metric: **{metric_label}**."
    )

    return _cap(positives), _cap(negatives), _cap(neutrals)
