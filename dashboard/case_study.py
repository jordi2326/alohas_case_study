"""Case-study answers for the Alohas recruiting exercise."""

from __future__ import annotations

import pandas as pd
import streamlit as st


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


def render_case_study_tab(
    channel_df: pd.DataFrame,
    wholesale_df: pd.DataFrame,
) -> None:
    st.markdown("#### Case study answers")
    st.caption(
        "How this dashboard and dbt model answer the three recruiting questions. "
        "Examples below use your current sidebar filters."
    )

    live_gaps = _margin_vs_revenue_gap(channel_df)

    with st.container(border=True):
        st.markdown("##### 01 — Channel sales")
        st.markdown(
            """
**How is the business performing across channels?**

**Time grain**  
- **Monthly** is the default strategic grain (`mart_channel_performance_monthly`): stable buckets,
  comparable to financial reporting, and aligned with how returns restate prior months.
- **Weekly** (and daily) in the Channels tab is for *tactical* monitoring when the period preset
  is short (e.g. last month uses weekly buckets over a full calendar month).
- Mix % and YoY comparisons should always use the **same grain** in numerator and denominator.

**Like-for-like**  
- Compare **net sales**, **return rate** (returned ÷ sold units), and **contribution margin %**
  together — revenue alone hides returns and cost structure.
- **Taxes** are in the model but margin is built on net sales after returns; channel mix shifts
  (e.g. online gaining share) change blended return rate even if each channel is flat.
- YoY on the dashboard uses the **same calendar months** one year apart (not rolling 12 unless
  the preset implies it).

**CEO vs Head of Wholesale — what to show first**

| Audience | First screen | Why |
| --- | --- | --- |
| **CEO** | Net sales + YoY, channel **mix %**, margin % by channel | Is the business growing, and is mix moving toward higher- or lower-margin channels? |
| **Head of Wholesale** | Country map, category bars, country × category heatmap, wholesale margin % | Revenue is negotiated by country and assortment; they need geo × category, not channel league table. |

This repo implements that split: **Channels** tab for CEO-style channel scorecard; **Countries → Wholesale**
for the wholesale operating view.
            """
        )
        snap = _channel_snapshot(channel_df)
        if snap is not None:
            st.markdown("**Current filter — channel snapshot**")
            display = snap.assign(
                net_sales=lambda d: d["net_sales"].map(lambda v: f"€{v:,.0f}"),
                mix_pct=lambda d: d["mix_pct"].map(lambda v: f"{v:.1%}"),
                return_rate=lambda d: d["return_rate"].map(lambda v: f"{v:.1%}"),
                margin_pct=lambda d: d["margin_pct"].map(lambda v: f"{v:.1%}"),
            )[["channel", "net_sales", "mix_pct", "return_rate", "margin_pct"]]
            st.dataframe(display, use_container_width=True, hide_index=True)
        for line in live_gaps:
            st.markdown(line)

    with st.container(border=True):
        st.markdown("##### 02 — Net sales and late-arriving returns")
        st.markdown(
            """
**Problem**  
`fct_sale_order_line` is **mutable**: `quantity_returned` and `net_sales` on a sale row are updated
in place when a return lands 30–90 days later. A dashboard that reads “as-is” always shows
**latest truth**, but **historical months change** when you re-run the pipeline.

**Proposed schema**

```
fct_sale_order_line_snapshot   -- immutable at sale time (append-only)
  sale_line_id (PK)
  channel, sku, shipment_id
  quantity_sold, gross_sale, taxes
  net_sales_at_sale            -- frozen when sold
  sold_at (created_at)

fct_return_event               -- one row per return movement (append-only)
  return_event_id (PK)
  sale_line_id (FK)
  quantity_returned_delta
  return_value_delta           -- impact on net_sales
  returned_at

fct_sale_order_line_current    -- optional convenience view: snapshot + sum(returns)
```

**Metric definitions to defend**

| Metric | Definition | Use when |
| --- | --- | --- |
| **Net sales (as-of sale date)** | `net_sales_at_sale` aggregated by `sold_at` month | Locked management reports, bonuses, board packs |
| **Net sales (as-of report date)** | Current `net_sales` on the line, by sale month | Operations, finance close, “true economics today” |
| **Return rate (as-of report date)** | `quantity_returned / quantity_sold` on current row | Quality and leakage monitoring (expect restatements) |

**How charts should behave**

- **Months 0–3 after sale month**: show as **provisional** (dashed line or “pending returns” band).
  Return rate typically **understates** final truth.
- **Month 4+**: treat as **mature** for flash reporting; still allow **restated** series when
  `fct_return_event` adds rows (second line or shaded revision).
- **Six months from now**: September sales today look strong; in March, September bars **drop**
  when returns post — the chart should show **revision arrows** or a toggle:
  *“View: as first reported | as of today”*.

**What we do today**  
Marts read **current** `net_sales` on the sale row (report-date view). That is honest if labeled;
it is misleading if users think months are frozen. The Data quality tab and gold filters do not
fix mutability — only an event/snapshot model does.
            """
        )

    with st.container(border=True):
        st.markdown("##### 03 — Contribution margin")
        st.markdown(
            """
**Definition in this project** (`fct_sales_enriched` → marts)

```
product_cost          = quantity_sold × dim_product.cost
allocated_shipping    = (line net_sales / shipment net_sales) × fct_shipment.shipping_cost
contribution_margin   = net_sales − product_cost − allocated_shipping
contribution_margin_% = contribution_margin / net_sales
```

**Assumptions (explicit)**

1. **Product cost** — unit cost at sale time from `dim_product`; no cost restatement on return
   (return economics flow through `net_sales`, not a separate return handling cost in source).
2. **Shipping** — outbound cost allocated **pro-rata by net sales within the shipment** (multi-line
   orders split shipping by revenue share). We do **not** claw back shipping on returned units unless
   `net_sales` on the line already reflects the refund.
3. **Returns** — embedded in `net_sales` and `quantity_returned` on the same row; margin uses
   **current** net sales (see Q02 — months can restate).
4. **Exclusions** — gold layer drops orphan SKU/shipment, null cost/country, invalid unit logic
   (see Data quality tab).

**Where to slice**

| Slice | Question it answers |
| --- | --- |
| **Channel** | Which go-to-market motion is profitable after logistics? |
| **Category** (wholesale mart) | Which assortment earns margin vs merely revenue? |
| **Country × category** | Where should wholesale invest vs prune? |

**Revenue vs margin — what to look for**  
Channels (or categories) with **high net sales and lower margin %** subsidize the P&L on volume;
**high margin % but small mix %** are niche profit pools. Compare the Channels tab margin chart
to the net sales chart — divergence is the story.
            """
        )
        snap = _channel_snapshot(channel_df)
        if snap is not None:
            st.markdown("**Current filter — margin ranking vs revenue ranking**")
            ranked = snap.assign(
                revenue_rank=snap["net_sales"].rank(ascending=False).astype(int),
                margin_rank=snap["margin_pct"].rank(ascending=False).astype(int),
            ).sort_values("revenue_rank")
            st.dataframe(
                ranked[
                    ["channel", "revenue_rank", "margin_rank", "net_sales", "margin_pct"]
                ].assign(
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
                st.markdown("**Wholesale — top categories by net sales (current filter)**")
                st.dataframe(
                    cat.assign(
                        net_sales=lambda d: d["net_sales"].map(lambda v: f"€{v:,.0f}"),
                        margin_pct=lambda d: d["margin_pct"].map(lambda v: f"{v:.1%}"),
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
