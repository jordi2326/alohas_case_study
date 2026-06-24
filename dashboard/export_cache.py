"""Export BigQuery results to dashboard/cache for offline / Streamlit Cloud deploy.

Run locally (needs `bq` CLI + gcloud auth):

    cd dashboard
    python export_cache.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from queries import (
    CHANNEL_DAILY_FALLBACK_QUERY,
    CHANNEL_PERFORMANCE_FALLBACK_QUERY,
    CHANNEL_WEEKLY_FALLBACK_QUERY,
    COUNTRY_DAILY_FALLBACK_QUERY,
    COUNTRY_PERFORMANCE_FALLBACK_QUERY,
    COUNTRY_WEEKLY_FALLBACK_QUERY,
    DATA_QUALITY_DETAIL_QUERIES,
    DATA_QUALITY_SUMMARY_QUERY,
    PROJECT_ID,
    WHOLESALE_PERFORMANCE_FALLBACK_QUERY,
)

CACHE_DIR = Path(__file__).resolve().parent / "cache"
NUMERIC_COLS = [
    "gross_sale", "taxes", "net_sales", "quantity_sold", "quantity_returned",
    "product_cost", "shipping_cost", "contribution_margin", "return_rate",
    "avg_order_value", "contribution_margin_pct", "pct_of_total_net_sales",
    "pct_of_channel_net_sales", "pct_of_wholesale_net_sales",
    "net_sales_prior_year", "return_rate_prior_year",
    "contribution_margin_pct_prior_year", "net_sales_yoy_pct",
    "return_rate_yoy_pp", "contribution_margin_pct_yoy_pp", "pct_of_table",
    "row_count", "cost", "base_price", "shipping_cost",
]


def _find_bq() -> str:
    for candidate in (
        shutil.which("bq"),
        shutil.which("bq.cmd"),
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Google", "Cloud SDK", "google-cloud-sdk", "bin", "bq.cmd",
        ),
    ):
        if candidate and os.path.isfile(candidate):
            return candidate
    raise RuntimeError("bq CLI not found. Run: gcloud auth application-default login")


def run_bq_query(query: str) -> pd.DataFrame:
    result = subprocess.run(
        [
            _find_bq(), "query", "--use_legacy_sql=false",
            "--format=json", "--quiet", "--max_rows=1000000",
        ],
        input=query,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "BigQuery query failed").strip())
    df = pd.DataFrame(json.loads(result.stdout or "[]"))
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("period_month", "period_date", "created_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    exports = {
        "channel_monthly": CHANNEL_PERFORMANCE_FALLBACK_QUERY.format(project=PROJECT_ID),
        "channel_daily": CHANNEL_DAILY_FALLBACK_QUERY.format(project=PROJECT_ID),
        "channel_weekly": CHANNEL_WEEKLY_FALLBACK_QUERY.format(project=PROJECT_ID),
        "country_monthly": COUNTRY_PERFORMANCE_FALLBACK_QUERY.format(project=PROJECT_ID),
        "country_daily": COUNTRY_DAILY_FALLBACK_QUERY.format(project=PROJECT_ID),
        "country_weekly": COUNTRY_WEEKLY_FALLBACK_QUERY.format(project=PROJECT_ID),
        "wholesale_monthly": WHOLESALE_PERFORMANCE_FALLBACK_QUERY.format(project=PROJECT_ID),
        "data_quality_summary": DATA_QUALITY_SUMMARY_QUERY.format(project=PROJECT_ID),
    }
    for name, query in exports.items():
        print(f"Exporting {name}...")
        df = run_bq_query(query)
        path = CACHE_DIR / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  -> {path} ({len(df):,} rows)")

    detail_dir = CACHE_DIR / "data_quality_detail"
    detail_dir.mkdir(exist_ok=True)
    for issue_type, template in DATA_QUALITY_DETAIL_QUERIES.items():
        print(f"Exporting data_quality_detail/{issue_type}...")
        query = template.format(project=PROJECT_ID, limit=100)
        df = run_bq_query(query)
        df.to_parquet(detail_dir / f"{issue_type}.parquet", index=False)
        print(f"  -> {len(df):,} rows")

    print(f"\nDone. Commit dashboard/cache/ and set DASHBOARD_DATA_SOURCE=cache on Streamlit Cloud.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
