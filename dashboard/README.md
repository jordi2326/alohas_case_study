# Channel Performance Dashboard

Streamlit dashboard for channel, country, wholesale, and data-quality
performance. Primary dashboard data is loaded from the dbt datamart in BigQuery;
fallback queries and cache export can use the same metric logic when the
datamart is not available locally.

## Run

```bash
pip install -r ../requirements.txt
gcloud auth application-default login
cd dashboard
streamlit run app.py
```

Open http://localhost:8501

## Structure

| File | Role |
|------|------|
| `app.py` | Streamlit UI and filters |
| `charts.py` | Plotly charts |
| `data.py` | BigQuery loading and helpers |
| `queries.py` | SQL against `dbt_dev_datamart` plus fallback/source-quality SQL |
| `theme.py` | CSS and metric tooltips |

## Data sources by view

| Dashboard view | Main table(s) |
|----------------|---------------|
| `Channel scorecard` | `mart_channel_performance_daily`, `mart_channel_performance_weekly`, or `mart_channel_performance_monthly`, depending on selected date preset |
| `Countries & wholesale` → `All channels` | `mart_country_performance_monthly` |
| `Countries & wholesale` → `Wholesale · category` | `mart_wholesale_performance_monthly` |
| `Countries & wholesale` → `All channels · country × category` | `mart_country_channel_category_performance_monthly` |
| `01 · Channel sales` | channel performance mart for the active granularity |
| `02 · Returns` | explanatory case-study page; does not load an extra mart |
| `03 · Margin` | channel performance mart plus `mart_wholesale_performance_monthly` and `mart_country_performance_monthly` context |
| `Data tables` | active channel mart and `mart_country_performance_monthly` |
| `Data quality` | direct `production.*` checks by design, because this view shows source rows excluded from gold/datamart models |

Daily, weekly, and monthly channel/country marts are not duplicates: they serve
different chart grains selected by the dashboard presets. Wholesale and all-channel
category marts also differ by grain and business question.
