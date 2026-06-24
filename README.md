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
    mart_channel_performance_monthly.sql
    mart_country_performance_monthly.sql
    mart_wholesale_performance_monthly.sql
```

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
