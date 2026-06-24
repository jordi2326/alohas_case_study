# Alohas Case Study — dbt + BigQuery

dbt project connected to the **alohas-recruiting-study-case** GCP project.

## Prerequisites

- Python 3.10+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`, `bq`)
- Access to the `production` dataset in BigQuery

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Authenticate with BigQuery

Application Default Credentials (ADC) are required for dbt:

```bash
gcloud auth application-default login
```

On Linux/macOS, credentials are saved to:

`~/.config/gcloud/application_default_credentials.json`

On Windows:

`%APPDATA%\gcloud\application_default_credentials.json`

Optional — point dbt at a specific credentials file:

```powershell
# PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS = "$env:APPDATA\gcloud\application_default_credentials.json"
```

```bash
# Linux/macOS
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json
```

### 3. Verify connection

```bash
dbt debug --profiles-dir .
```

### 4. Install packages and run models

```bash
dbt deps --profiles-dir .
dbt build --select gold+ --profiles-dir .
```

## Project structure

```
models/
  gold/             # cleaned views over production sources
    gold_dim_product.sql
    gold_fct_sale_order_line.sql
    gold_fct_shipment.sql
  datamart/         # business-ready facts and analytics
    fct_sales_enriched.sql
    mart_channel_performance_daily.sql
    mart_channel_performance_monthly.sql
    mart_channel_performance_weekly.sql
    mart_country_channel_category_performance_monthly.sql
    mart_country_performance_daily.sql
    mart_country_performance_monthly.sql
    mart_country_performance_weekly.sql
    mart_wholesale_performance_monthly.sql
```

## Datamart tables used by the dashboard

The Streamlit dashboard reads from `alohas-recruiting-study-case.dbt_dev_datamart`
when those dbt models are available. Inline SQL in `dashboard/queries.py` is kept
only as a fallback for local/dev runs before the datamart has been built.

| dbt model | Grain | Dashboard usage | Why it is not a duplicate |
|-----------|-------|-----------------|---------------------------|
| `fct_sales_enriched` | order line | Upstream base for every mart | Adds product/category/cost, shipment/country, and allocated shipping to cleaned gold order lines. It is not shown directly in the UI. |
| `mart_channel_performance_daily` | day x channel | `Channel scorecard`, `01 · Channel sales`, `03 · Margin`, and `Data tables` when short presets use daily charts | Same business metrics as the monthly channel mart, but different time grain required for daily chart presets. |
| `mart_channel_performance_weekly` | week x channel | Same channel views when medium presets use weekly charts | Same dimensions as daily/monthly channel marts, but week grain avoids overplotting medium ranges. |
| `mart_channel_performance_monthly` | month x channel | Sidebar metadata, default `Channel scorecard`, `01 · Channel sales`, `03 · Margin`, and channel CSV export | Monthly leadership scorecard with YoY fields. Not duplicated by daily/weekly because monthly includes prior-year comparisons at month grain. |
| `mart_country_performance_daily` | day x channel x country | Preset-aware country filtering helpers for short ranges | Daily country grain is needed by the shared preset/date logic; monthly country data is too coarse for short presets. |
| `mart_country_performance_weekly` | week x channel x country | Preset-aware country filtering helpers for medium ranges | Weekly country grain serves medium-range charts without duplicating the monthly YoY mart. |
| `mart_country_performance_monthly` | month x channel x country | `Countries & wholesale` → `All channels`, `03 · Margin`, and `Data tables` country table/CSV | Monthly country scorecard with channel share and YoY fields. It is the canonical country mart for map/heatmap views. |
| `mart_wholesale_performance_monthly` | month x country x category | `Countries & wholesale` → `Wholesale · category`, plus wholesale context in case-study views | Wholesale has a different business grain: country x product category for partner planning. It is not covered by the channel or country marts. |
| `mart_country_channel_category_performance_monthly` | month x country x channel x category | `Countries & wholesale` → `All channels · country × category` | Adds category to all channels, not only wholesale. It is intentionally separate from the wholesale mart because it compares every channel. |

### Non-mart dashboard queries

`dashboard/queries.py` still contains fallback SQL that rebuilds the same metrics
from `production.*` with the gold-layer data quality filters. Those queries are
used only when BigQuery cannot read the dbt datamart yet. The `Data quality` tab
intentionally queries `production.*` directly because it reports source issues
that the gold/datamart layers exclude.

## Source data

| Table | Description |
|-------|-------------|
| `production.dim_product` | Product catalog (SKU, price, cost) |
| `production.fct_sale_order_line` | Order lines (partitioned by `created_at`) |
| `production.fct_shipment` | Shipment details |

## Configuration

- **Profile:** `alohas_case_studio` (see `profiles.yml`)
- **Target dataset:** `dbt_dev` (EU region)
- **Sources:** `alohas-recruiting-study-case.production`
