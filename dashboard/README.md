# Channel Performance Dashboard

Streamlit dashboard for channel and country performance. Data is loaded from BigQuery via the `bq` CLI.

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
| `queries.py` | SQL against `production.*` |
| `theme.py` | CSS and metric tooltips |
