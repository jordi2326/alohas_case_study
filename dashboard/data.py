from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from queries import (
    CHANNEL_DAILY_FALLBACK_QUERY,
    CHANNEL_DAILY_QUERY,
    CHANNEL_PERFORMANCE_FALLBACK_QUERY,
    CHANNEL_PERFORMANCE_QUERY,
    CHANNEL_WEEKLY_FALLBACK_QUERY,
    CHANNEL_WEEKLY_QUERY,
    COUNTRY_DAILY_FALLBACK_QUERY,
    COUNTRY_DAILY_QUERY,
    COUNTRY_PERFORMANCE_FALLBACK_QUERY,
    COUNTRY_PERFORMANCE_QUERY,
    COUNTRY_WEEKLY_FALLBACK_QUERY,
    COUNTRY_WEEKLY_QUERY,
    DATA_QUALITY_DETAIL_QUERIES,
    DATA_QUALITY_SUMMARY_QUERY,
    DATAMART_DATASET,
    PROJECT_ID,
    SOURCE_DATASET,
    WHOLESALE_PERFORMANCE_FALLBACK_QUERY,
    WHOLESALE_PERFORMANCE_QUERY,
)

COUNTRY_NAME_MAP = {
    "ES": "Spain",
    "FR": "France",
    "DE": "Germany",
    "US": "United States",
    "IT": "Italy",
    "UK": "United Kingdom",
    "PT": "Portugal",
    "MX": "Mexico",
}

ISO3_MAP = {
    "ES": "ESP",
    "FR": "FRA",
    "DE": "DEU",
    "US": "USA",
    "IT": "ITA",
    "UK": "GBR",
    "PT": "PRT",
    "MX": "MEX",
}

METRIC_DEFINITIONS = {
    "Latest month": "End month of the selected period.",
    "Period": "Selected date range used for KPI totals and year-over-year comparisons.",
    "Net sales": "Realized revenue after returns and taxes.",
    "Units sold": "Total product units sold in the period.",
    "Return rate": "Returned units divided by sold units.",
    "Margin %": "Contribution margin as a percentage of net sales.",
    "Contribution margin": "Net sales minus product cost and allocated shipping.",
    "Mix %": "Share of total net sales within the same month across channels.",
    "Mix % (channel)": "Share of net sales within the same channel and month.",
    "Net sales YoY": "Year-over-year change in net sales vs. the same period one year earlier.",
    "YoY vs last year": "Percentage change versus the same period in the prior year.",
    "Top channel": "Channel with the highest net sales in the selected period.",
    "Top country": "Country with the highest net sales in the selected period.",
    "Avg return rate": "Weighted return rate (returned ÷ sold units) across the selected period.",
    "Channel": "Sales channel (online, retail, wholesale, marketplace).",
    "Month": "Calendar month of the order line.",
    "Map metric": "Metric displayed on the world choropleth map.",
    "Wholesale net sales": "Wholesale net sales across selected countries in the period.",
    "Wholesale return rate": "Weighted return rate for wholesale orders in the period.",
    "Wholesale margin": "Wholesale contribution margin as a % of net sales.",
    "Top wholesale country": "Country with the highest wholesale net sales in the period.",
    "Top wholesale category": "Product category with the highest wholesale net sales in the period.",
}

MAP_METRIC_OPTIONS = {
    "net_sales": "Net sales",
    "quantity_sold": "Units sold",
    "return_rate": "Return rate",
    "contribution_margin": "Contribution margin",
    "contribution_margin_pct": "Margin %",
}

NUMERIC_COLS = [
    "gross_sale",
    "taxes",
    "net_sales",
    "quantity_sold",
    "quantity_returned",
    "product_cost",
    "shipping_cost",
    "contribution_margin",
    "return_rate",
    "avg_order_value",
    "contribution_margin_pct",
    "pct_of_total_net_sales",
    "pct_of_channel_net_sales",
    "pct_of_wholesale_net_sales",
    "net_sales_prior_year",
    "return_rate_prior_year",
    "contribution_margin_pct_prior_year",
    "net_sales_yoy_pct",
    "return_rate_yoy_pp",
    "contribution_margin_pct_yoy_pp",
]


CACHE_DIR = Path(__file__).resolve().parent / "cache"

_bq_client = None
_datamart_ready: bool | None = None
_data_source_resolved: str | None = None


def _cache_bundle_ok() -> bool:
    required = (
        "channel_monthly.parquet",
        "country_monthly.parquet",
        "wholesale_monthly.parquet",
    )
    return all((CACHE_DIR / name).is_file() for name in required)


def _configured_data_source() -> str:
    env = os.environ.get("DASHBOARD_DATA_SOURCE", "").strip().lower()
    if env in ("cache", "bq", "auto"):
        return env
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "DASHBOARD_DATA_SOURCE" in st.secrets:
                value = str(st.secrets["DASHBOARD_DATA_SOURCE"]).strip().lower()
                if value in ("cache", "bq", "auto"):
                    return value
            if "dashboard" in st.secrets and "data_source" in st.secrets["dashboard"]:
                value = str(st.secrets["dashboard"]["data_source"]).strip().lower()
                if value in ("cache", "bq", "auto"):
                    return value
    except Exception:
        pass
    return "auto"


def using_cached_data() -> bool:
    global _data_source_resolved
    mode = _configured_data_source()
    if mode == "cache":
        return True
    if mode == "bq":
        return False
    if _data_source_resolved == "cache":
        return True
    if _data_source_resolved == "bq":
        return False
    if _cache_bundle_ok():
        try:
            _run_bq_query("SELECT 1 AS ok")
            _data_source_resolved = "bq"
            return False
        except Exception:
            _data_source_resolved = "cache"
            return True
    _data_source_resolved = "bq"
    return False


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "period_month" in df.columns:
        df["period_month"] = pd.to_datetime(df["period_month"])
    if "period_date" in df.columns:
        df["period_date"] = pd.to_datetime(df["period_date"])
    return df


def _read_cache(name: str) -> pd.DataFrame:
    path = CACHE_DIR / f"{name}.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"Missing cache file: {path}")
    return _normalize_dataframe(pd.read_parquet(path))


def _credentials_from_streamlit_secrets():
    try:
        import streamlit as st
    except Exception:
        return None
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account
            return service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"])
            )
    except Exception:
        return None
    return None


def _credentials_from_env():
    try:
        from google.oauth2 import service_account
    except ImportError:
        return None
    raw_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if raw_json:
        return service_account.Credentials.from_service_account_info(
            json.loads(raw_json)
        )
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.isfile(creds_path):
        return service_account.Credentials.from_service_account_file(creds_path)
    return None


def _get_bq_client():
    global _bq_client
    if _bq_client is not None:
        return _bq_client
    from google.cloud import bigquery
    credentials = _credentials_from_streamlit_secrets() or _credentials_from_env()
    if credentials is not None:
        _bq_client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
    else:
        _bq_client = bigquery.Client(project=PROJECT_ID)
    return _bq_client


def _run_bq_query(query: str) -> pd.DataFrame:
    from google.cloud import bigquery
    job_config = bigquery.QueryJobConfig(use_legacy_sql=False)
    df = _get_bq_client().query(query, job_config=job_config).to_dataframe()
    return _normalize_dataframe(df)


def datamart_available() -> bool:
    if using_cached_data():
        return False
    global _datamart_ready
    if _datamart_ready is not None:
        return _datamart_ready
    probe = (
        f"SELECT 1 AS ok "
        f"FROM `{PROJECT_ID}.{DATAMART_DATASET}.mart_channel_performance_monthly` "
        f"LIMIT 1"
    )
    try:
        _run_bq_query(probe)
        _datamart_ready = True
    except Exception:
        _datamart_ready = False
    return _datamart_ready


def analytics_data_source_label() -> str:
    if using_cached_data():
        return "dashboard/cache (snapshot — no live BigQuery)"
    if datamart_available():
        return f"{PROJECT_ID}.{DATAMART_DATASET}"
    return f"{PROJECT_ID}.{SOURCE_DATASET} (inline gold DQ filters)"


def _pick_query(datamart_query: str, fallback_query: str) -> str:
    template = datamart_query if datamart_available() else fallback_query
    return template.format(project=PROJECT_ID)


def _rename_period_column(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    if "period_date" in df.columns and target_col != "period_date":
        df = df.rename(columns={"period_date": target_col})
    return df


def load_channel_performance(granularity: str = "month") -> pd.DataFrame:
    if using_cached_data():
        key = {"month": "channel_monthly", "day": "channel_daily", "week": "channel_weekly"}[granularity]
        df = _read_cache(key)
        if granularity == "day":
            return _rename_period_column(df, "period_day")
        if granularity == "week":
            return _rename_period_column(df, "period_week")
        return df
    if granularity == "day":
        query = _pick_query(CHANNEL_DAILY_QUERY, CHANNEL_DAILY_FALLBACK_QUERY)
        return _rename_period_column(_run_bq_query(query), "period_day")
    if granularity == "week":
        query = _pick_query(CHANNEL_WEEKLY_QUERY, CHANNEL_WEEKLY_FALLBACK_QUERY)
        return _rename_period_column(_run_bq_query(query), "period_week")
    query = _pick_query(CHANNEL_PERFORMANCE_QUERY, CHANNEL_PERFORMANCE_FALLBACK_QUERY)
    return _run_bq_query(query)


def load_country_performance(granularity: str = "month") -> pd.DataFrame:
    if using_cached_data():
        key = {"month": "country_monthly", "day": "country_daily", "week": "country_weekly"}[granularity]
        df = _read_cache(key)
        if granularity == "day":
            df = _rename_period_column(df, "period_day")
        elif granularity == "week":
            df = _rename_period_column(df, "period_week")
    elif granularity == "day":
        query = _pick_query(COUNTRY_DAILY_QUERY, COUNTRY_DAILY_FALLBACK_QUERY)
        df = _rename_period_column(_run_bq_query(query), "period_day")
    elif granularity == "week":
        query = _pick_query(COUNTRY_WEEKLY_QUERY, COUNTRY_WEEKLY_FALLBACK_QUERY)
        df = _rename_period_column(_run_bq_query(query), "period_week")
    else:
        query = _pick_query(COUNTRY_PERFORMANCE_QUERY, COUNTRY_PERFORMANCE_FALLBACK_QUERY)
        df = _run_bq_query(query)
    df["country_name"] = df["country"].map(COUNTRY_NAME_MAP).fillna(df["country"])
    df["iso_alpha"] = df["country"].map(ISO3_MAP).fillna(df["country"])
    return df


def load_wholesale_performance() -> pd.DataFrame:
    if using_cached_data():
        df = _read_cache("wholesale_monthly")
    else:
        query = _pick_query(WHOLESALE_PERFORMANCE_QUERY, WHOLESALE_PERFORMANCE_FALLBACK_QUERY)
        df = _run_bq_query(query)
    df["country_name"] = df["country"].map(COUNTRY_NAME_MAP).fillna(df["country"])
    df["iso_alpha"] = df["country"].map(ISO3_MAP).fillna(df["country"])
    return df

DATA_QUALITY_CHECK_META = {
    "orphan_sku": {
        "checked_in": (
            "`{project}.production.fct_sale_order_line` "
            "LEFT JOIN `{project}.production.dim_product` ON sku"
        ),
        "check_rule": "SKU not in dim_product (p.sku IS NULL)",
        "validated_against_table": "dim_product",
        "example_table_path": "`{project}.production.fct_sale_order_line`",
        "record_key_fields": ["sku", "shipment_id", "created_at"],
    },
    "orphan_shipment": {
        "checked_in": (
            "`{project}.production.fct_sale_order_line` "
            "LEFT JOIN `{project}.production.fct_shipment` ON shipment_id"
        ),
        "check_rule": "shipment_id not in fct_shipment (s.shipment_id IS NULL)",
        "validated_against_table": "fct_shipment",
        "example_table_path": "`{project}.production.fct_sale_order_line`",
        "record_key_fields": ["shipment_id", "sku", "created_at"],
    },
    "returns_exceed_sold": {
        "checked_in": "`{project}.production.fct_sale_order_line`",
        "check_rule": "quantity_returned > quantity_sold",
        "validated_against_table": None,
        "example_table_path": "`{project}.production.fct_sale_order_line`",
        "record_key_fields": ["sku", "shipment_id", "created_at"],
    },
    "negative_net_sales": {
        "checked_in": "`{project}.production.fct_sale_order_line`",
        "check_rule": "net_sales < 0",
        "validated_against_table": None,
        "example_table_path": "`{project}.production.fct_sale_order_line`",
        "record_key_fields": ["sku", "shipment_id", "created_at"],
    },
    "zero_quantity_sold": {
        "checked_in": "`{project}.production.fct_sale_order_line`",
        "check_rule": "quantity_sold = 0",
        "validated_against_table": None,
        "example_table_path": "`{project}.production.fct_sale_order_line`",
        "record_key_fields": ["sku", "shipment_id", "created_at"],
    },
    "null_country": {
        "checked_in": "`{project}.production.fct_shipment`",
        "check_rule": "country IS NULL",
        "validated_against_table": None,
        "example_table_path": "`{project}.production.fct_shipment`",
        "record_key_fields": ["shipment_id"],
    },
    "null_cost": {
        "checked_in": "`{project}.production.dim_product`",
        "check_rule": "cost IS NULL",
        "validated_against_table": None,
        "example_table_path": "`{project}.production.dim_product`",
        "record_key_fields": ["sku"],
    },
}


def _table_path(table: str | None) -> str:
    if not table:
        return "—"
    return f"{PROJECT_ID}.{SOURCE_DATASET}.{table}"


def _format_check_meta(issue_type: str) -> dict[str, str]:
    raw = DATA_QUALITY_CHECK_META.get(issue_type, {})
    return {
        key: value.format(project=PROJECT_ID)
        for key, value in raw.items()
        if isinstance(value, str)
    }


def _build_record_key(row: pd.Series, fields: list[str]) -> str:
    parts = []
    for field in fields:
        if field not in row.index or pd.isna(row[field]):
            continue
        value = row[field]
        if isinstance(value, pd.Timestamp):
            value = value.strftime("%Y-%m-%d %H:%M")
        parts.append(f"{field}={value}")
    return " | ".join(parts)


def _enrich_data_quality_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    enriched = df.copy()
    enriched["checked_in"] = enriched["issue_type"].map(
        lambda issue: _format_check_meta(issue).get("checked_in", "")
    )
    enriched["check_rule"] = enriched["issue_type"].map(
        lambda issue: _format_check_meta(issue).get("check_rule", "")
    )
    enriched["example_table_path"] = enriched["issue_type"].map(
        lambda issue: _format_check_meta(issue).get("example_table_path", "")
    )
    enriched["validated_against"] = enriched["issue_type"].map(
        lambda issue: _table_path(
            DATA_QUALITY_CHECK_META.get(issue, {}).get("validated_against_table")
        )
    )
    enriched["source_location"] = enriched["source_table"].map(
        lambda table: _table_path(table)
    )
    return enriched


def _enrich_data_quality_detail(df: pd.DataFrame, issue_type: str) -> pd.DataFrame:
    if df.empty:
        return df
    meta = _format_check_meta(issue_type)
    key_fields = DATA_QUALITY_CHECK_META.get(issue_type, {}).get("record_key_fields", [])
    enriched = df.copy()
    enriched.insert(0, "record_key", enriched.apply(
        lambda row: _build_record_key(row, key_fields), axis=1,
    ))
    enriched.insert(0, "record_table", meta.get("example_table_path", ""))
    return enriched


def load_data_quality_summary() -> pd.DataFrame:
    if using_cached_data():
        df = _read_cache("data_quality_summary")
    else:
        query = DATA_QUALITY_SUMMARY_QUERY.format(project=PROJECT_ID)
        df = _run_bq_query(query)
    if "pct_of_table" in df.columns:
        df["pct_of_table"] = pd.to_numeric(df["pct_of_table"], errors="coerce")
    if "row_count" in df.columns:
        df["row_count"] = pd.to_numeric(df["row_count"], errors="coerce")
    return _enrich_data_quality_summary(df)


def load_data_quality_detail(issue_type: str, limit: int = 100) -> pd.DataFrame:
    if using_cached_data():
        path = CACHE_DIR / "data_quality_detail" / f"{issue_type}.parquet"
        if not path.is_file():
            return pd.DataFrame()
        df = _normalize_dataframe(pd.read_parquet(path))
        if limit and len(df) > limit:
            df = df.head(limit)
    else:
        query_template = DATA_QUALITY_DETAIL_QUERIES.get(issue_type)
        if not query_template:
            return pd.DataFrame()
        query = query_template.format(project=PROJECT_ID, limit=limit)
        df = _run_bq_query(query)
    for col in ("gross_sale", "net_sales", "quantity_sold", "quantity_returned", "shipping_cost", "cost", "base_price"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return _enrich_data_quality_detail(df, issue_type)


def prepare_data_quality_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    renamed = df.rename(
        columns={
            "source_table": "Source table",
            "source_location": "Record source",
            "validated_against": "Checked against",
            "check_rule": "Check rule",
            "issue_type": "Issue code",
            "issue_description": "Issue",
            "severity": "Severity",
            "row_count": "Affected rows",
            "pct_of_table": "% of table",
        }
    )
    preferred = [
        "Issue",
        "Severity",
        "Affected rows",
        "% of table",
        "Record source",
        "Checked against",
        "Check rule",
    ]
    cols = [col for col in preferred if col in renamed.columns]
    return renamed[cols]


def prepare_data_quality_detail_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    display = df.copy()
    if "created_at" in display.columns:
        display["created_at"] = pd.to_datetime(display["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    column_labels = {
        "record_key": "Record key",
        "record_table": "Record table",
        "channel": "Channel",
        "sku": "SKU",
        "shipment_id": "Shipment ID",
        "quantity_sold": "Units sold",
        "quantity_returned": "Units returned",
        "gross_sale": "Gross sale",
        "net_sales": "Net sales",
        "created_at": "Created at",
        "shipping_method": "Shipping method",
        "shipping_cost": "Shipping cost",
        "country": "Country",
        "name": "Product name",
        "category": "Category",
        "base_price": "Base price",
        "cost": "Cost",
    }
    return display.rename(columns=column_labels)


def filter_wholesale_data(
    df: pd.DataFrame,
    start_date,
    end_date,
    countries: list[str] | None = None,
    categories: list[str] | None = None,
) -> pd.DataFrame:
    start = pd.Timestamp(start_date).to_period("M").to_timestamp()
    end = pd.Timestamp(end_date).to_period("M").to_timestamp()
    mask = (df["period_month"] >= start) & (df["period_month"] <= end)
    if countries is not None:
        mask &= df["country"].isin(countries)
    if categories is not None:
        mask &= df["category"].isin(categories)
    return df.loc[mask].copy()


def resolve_period_col(df: pd.DataFrame) -> str:
    for column in ("period_day", "period_week", "period_month"):
        if column in df.columns:
            return column
    return "period_month"


def preset_granularity(preset: str) -> str:
    mapping = {
        "last_week": "day",
        "last_month": "week",
        "weekly": "week",
        "last_6_months": "month",
        "last_1_year": "month",
    }
    return mapping.get(preset, "month")


def period_col_for_granularity(granularity: str) -> str:
    return {
        "day": "period_day",
        "week": "period_week",
        "month": "period_month",
    }[granularity]


def load_active_performance(preset: str) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    granularity = preset_granularity(preset if preset in PERIOD_PRESETS else "last_1_year")
    return (
        load_channel_performance(granularity),
        load_country_performance(granularity),
        granularity,
    )


def filter_data(
    df: pd.DataFrame,
    channels: list[str],
    start_date,
    end_date,
    countries: list[str] | None = None,
    period_col: str | None = None,
) -> pd.DataFrame:
    period_col = period_col or resolve_period_col(df)
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    if period_col == "period_month":
        start = start.to_period("M").to_timestamp()
        end = end.to_period("M").to_timestamp()
    mask = (
        df["channel"].isin(channels)
        & (df[period_col] >= start)
        & (df[period_col] <= end)
    )
    if countries is not None and "country" in df.columns:
        mask &= df["country"].isin(countries)
    return df.loc[mask].copy()


def latest_period(df: pd.DataFrame) -> pd.Timestamp | None:
    if df.empty:
        return None
    period_col = resolve_period_col(df)
    return df[period_col].max()


def prior_year_period(latest: pd.Timestamp) -> pd.Timestamp:
    return latest - pd.DateOffset(years=1)


def default_period_last_year(*dfs: pd.DataFrame) -> tuple:
    """Last 12 months ending at the latest month shared by all datasets."""
    max_ts = min(df["period_month"].max() for df in dfs)
    min_ts = min(df["period_month"].min() for df in dfs)
    start = (max_ts - pd.DateOffset(months=11)).replace(day=1)
    if start < min_ts:
        start = min_ts.replace(day=1)
    return start.date(), (max_ts + pd.offsets.MonthEnd(0)).date()


def default_period_last_year_channel(df: pd.DataFrame) -> tuple:
    """Last 12 months of channel data (default dashboard period)."""
    return period_for_preset("last_1_year", df, bounds_min=None, bounds_max=None)


PERIOD_PRESETS = {
    "last_week": "Last week",
    "last_month": "Last month",
    "weekly": "Weekly",
    "last_6_months": "Last 6 months",
    "last_1_year": "Last 1 year",
}


def period_for_preset(
    preset: str,
    *dfs: pd.DataFrame,
    bounds_min=None,
    bounds_max=None,
) -> tuple:
    granularity = preset_granularity(preset)
    period_col = period_col_for_granularity(granularity)
    max_ts = max(df[period_col].max() for df in dfs)
    min_ts = min(df[period_col].min() for df in dfs)
    end_ts = max_ts.normalize()

    if preset == "last_week":
        start_ts = end_ts - pd.Timedelta(days=6)
    elif preset == "last_month":
        start_ts = end_ts.replace(day=1)
        end_ts = end_ts + pd.offsets.MonthEnd(0)
    elif preset == "weekly":
        start_ts = end_ts - pd.Timedelta(weeks=7)
    elif preset == "last_6_months":
        start_ts = (max_ts - pd.DateOffset(months=5)).replace(day=1)
        end_ts = max_ts + pd.offsets.MonthEnd(0)
    elif preset == "last_1_year":
        start_ts = (max_ts - pd.DateOffset(months=11)).replace(day=1)
        end_ts = max_ts + pd.offsets.MonthEnd(0)
    else:
        start_ts = min_ts.normalize()
        end_ts = max_ts + pd.offsets.MonthEnd(0) if period_col == "period_month" else end_ts

    if start_ts < min_ts:
        start_ts = min_ts.normalize()

    start_date = start_ts.date()
    end_date = end_ts.date()
    if bounds_min is not None and bounds_max is not None:
        return clamp_period(start_date, end_date, bounds_min, bounds_max)
    return start_date, end_date


def match_period_preset(
    start_date,
    end_date,
    *dfs: pd.DataFrame,
    bounds_min,
    bounds_max,
    granularity: str | None = None,
) -> str | None:
    for preset in PERIOD_PRESETS:
        if granularity and preset_granularity(preset) != granularity:
            continue
        preset_start, preset_end = period_for_preset(
            preset,
            *dfs,
            bounds_min=bounds_min,
            bounds_max=bounds_max,
        )
        if preset_start == start_date and preset_end == end_date:
            return preset
    return None


def data_bounds(df: pd.DataFrame) -> tuple:
    period_col = resolve_period_col(df)
    min_ts = df[period_col].min()
    max_ts = df[period_col].max()
    if period_col == "period_month":
        return min_ts.date(), (max_ts + pd.offsets.MonthEnd(0)).date()
    return min_ts.date(), max_ts.date()


def picker_date_bounds(*dfs: pd.DataFrame) -> tuple:
    min_ts = min(df[resolve_period_col(df)].min() for df in dfs)
    max_ts = max(df[resolve_period_col(df)].max() for df in dfs)
    period_col = resolve_period_col(dfs[0])
    if period_col == "period_month":
        return min_ts.date(), (max_ts + pd.offsets.MonthEnd(0)).date()
    return min_ts.date(), max_ts.date()


def clamp_period(start_date, end_date, min_date, max_date) -> tuple:
    start = max(min(pd.Timestamp(start_date).date(), max_date), min_date)
    end = max(min(pd.Timestamp(end_date).date(), max_date), min_date)
    if start > end:
        start, end = end, start
    return start, end


def intersect_period(start_date, end_date, bounds_min, bounds_max) -> tuple | None:
    effective_start = max(start_date, bounds_min)
    effective_end = min(end_date, bounds_max)
    if effective_start > effective_end:
        return None
    return effective_start, effective_end


def prior_year_range(start_date, end_date) -> tuple:
    start = pd.Timestamp(start_date) - pd.DateOffset(years=1)
    end = pd.Timestamp(end_date) - pd.DateOffset(years=1)
    return start.date(), end.date()


def format_period_label(start_date, end_date) -> str:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start.date() == end.date():
        return start.strftime("%d %b %Y")
    if (
        start.year == end.year
        and start.month == end.month
        and start.day == 1
        and end.normalize() == (start + pd.offsets.MonthEnd(0)).normalize()
    ):
        return start.strftime("%b %Y")
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%d')}–{end.strftime('%d %b %Y')}"
    if start.year == end.year:
        return f"{start.strftime('%d %b')} – {end.strftime('%d %b %Y')}"
    return f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"


def weighted_return_rate(frame: pd.DataFrame) -> float | None:
    sold = frame["quantity_sold"].sum()
    if sold == 0:
        return None
    return frame["quantity_returned"].sum() / sold


def compute_channel_kpis(
    df: pd.DataFrame,
    channels: list[str],
    start_date,
    end_date,
) -> dict:
    current = filter_data(df, channels, start_date, end_date)
    prior_start, prior_end = prior_year_range(start_date, end_date)
    prior = filter_data(df, channels, prior_start, prior_end)

    net_sales = current["net_sales"].sum()
    prior_net_sales = prior["net_sales"].sum()
    return_rate = weighted_return_rate(current)
    prior_return_rate = weighted_return_rate(prior)

    channel_totals = current.groupby("channel", as_index=False)["net_sales"].sum()
    top_channel = "—"
    if not channel_totals.empty:
        top_row = channel_totals.loc[channel_totals["net_sales"].idxmax()]
        top_channel = top_row["channel"]

    return {
        "period_label": format_period_label(start_date, end_date),
        "prior_period_label": format_period_label(prior_start, prior_end),
        "latest_month": latest_period(current),
        "net_sales": net_sales,
        "net_sales_yoy": yoy_pct(net_sales, prior_net_sales) if not prior.empty else None,
        "return_rate": return_rate,
        "return_rate_yoy": (
            yoy_pct(return_rate, prior_return_rate)
            if return_rate is not None and prior_return_rate is not None
            else None
        ),
        "top_channel": top_channel,
        "has_prior_period": not prior.empty,
    }


def compute_country_kpi(
    df: pd.DataFrame,
    channels: list[str],
    start_date,
    end_date,
    countries: list[str] | None = None,
) -> dict:
    current = filter_data(df, channels, start_date, end_date, countries=countries)
    prior_start, prior_end = prior_year_range(start_date, end_date)
    prior = filter_data(df, channels, prior_start, prior_end, countries=countries)

    country_totals = (
        current.groupby("country_name", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )
    top_country = "—"
    if not country_totals.empty:
        top_row = country_totals.iloc[0]
        top_country = top_row["country_name"]

    return {
        "period_label": format_period_label(start_date, end_date),
        "prior_period_label": format_period_label(prior_start, prior_end),
        "top_country": top_country,
        "has_prior_period": not prior.empty,
    }


def compute_wholesale_kpis(
    df: pd.DataFrame,
    start_date,
    end_date,
    countries: list[str] | None = None,
    categories: list[str] | None = None,
) -> dict:
    current = filter_wholesale_data(
        df, start_date, end_date, countries=countries, categories=categories,
    )
    prior_start, prior_end = prior_year_range(start_date, end_date)
    prior = filter_wholesale_data(
        df, prior_start, prior_end, countries=countries, categories=categories,
    )

    net_sales = current["net_sales"].sum()
    prior_net_sales = prior["net_sales"].sum()
    return_rate = weighted_return_rate(current)
    prior_return_rate = weighted_return_rate(prior)
    margin = current["contribution_margin"].sum()
    prior_margin = prior["contribution_margin"].sum()
    margin_pct = margin / net_sales if net_sales else None
    prior_margin_pct = prior_margin / prior_net_sales if prior_net_sales else None

    country_totals = (
        current.groupby("country_name", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )
    top_country = "—"
    top_country_share = None
    if not country_totals.empty:
        top_row = country_totals.iloc[0]
        top_country = top_row["country_name"]
        if net_sales:
            top_country_share = top_row["net_sales"] / net_sales

    category_totals = (
        current.groupby("category", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )
    top_category = "—"
    top_category_share = None
    if not category_totals.empty:
        top_row = category_totals.iloc[0]
        top_category = top_row["category"]
        if net_sales:
            top_category_share = top_row["net_sales"] / net_sales

    return {
        "period_label": format_period_label(start_date, end_date),
        "prior_period_label": format_period_label(prior_start, prior_end),
        "net_sales": net_sales,
        "net_sales_yoy": yoy_pct(net_sales, prior_net_sales) if not prior.empty else None,
        "return_rate": return_rate,
        "return_rate_yoy": (
            yoy_pct(return_rate, prior_return_rate)
            if return_rate is not None and prior_return_rate is not None
            else None
        ),
        "margin_pct": margin_pct,
        "margin_pct_yoy": (
            yoy_pct(margin_pct, prior_margin_pct)
            if margin_pct is not None and prior_margin_pct is not None
            else None
        ),
        "top_country": top_country,
        "top_country_share": top_country_share,
        "top_category": top_category,
        "top_category_share": top_category_share,
        "has_prior_period": not prior.empty,
    }


def aggregate_wholesale_categories(df: pd.DataFrame, metric: str = "net_sales") -> pd.DataFrame:
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
    return grouped.sort_values(metric, ascending=False)


def prepare_wholesale_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    display = df.copy()
    for col in (
        "net_sales",
        "quantity_sold",
        "return_rate",
        "contribution_margin_pct",
        "pct_of_wholesale_net_sales",
    ):
        if col in display.columns:
            display[col] = pd.to_numeric(display[col], errors="coerce")
    display["period_month"] = pd.to_datetime(display["period_month"]).dt.strftime("%Y-%m")
    display = display.rename(
        columns={
            "period_month": "Month",
            "country_name": "Country",
            "category": "Category",
            "net_sales": "Net sales",
            "quantity_sold": "Units sold",
            "return_rate": "Return rate",
            "contribution_margin_pct": "Margin %",
            "pct_of_wholesale_net_sales": "Mix % (wholesale)",
        }
    )
    return display[
        [
            "Month",
            "Country",
            "Category",
            "Net sales",
            "Units sold",
            "Return rate",
            "Margin %",
            "Mix % (wholesale)",
        ]
    ]


def top_country_summary(df: pd.DataFrame) -> tuple[str, float | None, pd.Timestamp | None]:
    if df.empty:
        return "—", None, None
    latest = latest_period(df)
    latest_slice = df[df["period_month"] == latest]
    totals = (
        latest_slice.groupby("country_name", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )
    if totals.empty:
        return "—", None, latest
    top_name = totals.iloc[0]["country_name"]
    top_sales = totals.iloc[0]["net_sales"]
    prior = df[
        (df["period_month"] == prior_year_period(latest))
        & (df["country_name"] == top_name)
    ]
    yoy = yoy_pct(top_sales, prior["net_sales"].sum()) if not prior.empty else None
    return top_name, yoy, latest


def yoy_pct(current: float, prior: float) -> float | None:
    if pd.isna(current) or pd.isna(prior) or prior == 0:
        return None
    return (current - prior) / prior


def format_yoy_delta(pct: float | None) -> str | None:
    if pct is None:
        return None
    return f"{pct:+.1%} vs prior period"


def aggregate_countries(df: pd.DataFrame, metric: str = "net_sales") -> pd.DataFrame:
    grouped = df.groupby(["country", "country_name", "iso_alpha"], as_index=False).agg(
        net_sales=("net_sales", "sum"),
        quantity_sold=("quantity_sold", "sum"),
        quantity_returned=("quantity_returned", "sum"),
        contribution_margin=("contribution_margin", "sum"),
    )
    grouped["return_rate"] = grouped["quantity_returned"] / grouped["quantity_sold"]
    grouped["contribution_margin_pct"] = (
        grouped["contribution_margin"] / grouped["net_sales"]
    )
    return grouped.sort_values(metric, ascending=False)


def prepare_summary_table(df: pd.DataFrame, by_country: bool = False) -> pd.DataFrame:
    display = df.copy()
    period_col = resolve_period_col(df)
    period_labels = {
        "period_day": "Day",
        "period_week": "Week",
        "period_month": "Month",
    }
    period_label = period_labels[period_col]
    if period_col == "period_day":
        display[period_col] = display[period_col].dt.strftime("%Y-%m-%d")
    elif period_col == "period_week":
        display[period_col] = display[period_col].dt.strftime("%Y-%m-%d")
    else:
        display[period_col] = display[period_col].dt.strftime("%Y-%m")

    if by_country:
        display = display.rename(
            columns={
                period_col: period_label,
                "channel": "Channel",
                "country_name": "Country",
                "net_sales": "Net sales",
                "quantity_sold": "Units sold",
                "return_rate": "Return rate",
                "contribution_margin_pct": "Margin %",
                "pct_of_channel_net_sales": "Mix % (channel)",
            }
        )
        cols = [
            period_label,
            "Channel",
            "Country",
            "Net sales",
            "Units sold",
            "Return rate",
            "Margin %",
            "Mix % (channel)",
        ]
    else:
        rename_map = {
            period_col: period_label,
            "channel": "Channel",
            "net_sales": "Net sales",
            "quantity_sold": "Units sold",
            "return_rate": "Return rate",
            "contribution_margin_pct": "Margin %",
            "pct_of_total_net_sales": "Mix %",
        }
        if "net_sales_yoy_pct" in display.columns:
            rename_map["net_sales_yoy_pct"] = "Net sales YoY"
        display = display.rename(columns=rename_map)
        cols = [
            period_label,
            "Channel",
            "Net sales",
            "Units sold",
            "Return rate",
            "Margin %",
            "Mix %",
        ]
        if "Net sales YoY" in display.columns:
            cols.append("Net sales YoY")

    return display[cols].copy()
