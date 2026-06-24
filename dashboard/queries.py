PROJECT_ID = "alohas-recruiting-study-case"
DATAMART_DATASET = "dbt_dev_datamart"
SOURCE_DATASET = "production"

FCT_SALES_ENRICHED_TABLE = f"`{{project}}.{DATAMART_DATASET}.fct_sales_enriched`"

# Mirrors gold-layer DQ rules when dbt datamart tables are not built yet.
FCT_SALES_ENRICHED_INLINE_CTES = """
products as (
    select sku, name, category, base_price, cost
    from `{project}.production.dim_product`
    where cost is not null
),
shipments as (
    select shipment_id, shipping_method, shipping_cost, country
    from `{project}.production.fct_shipment`
    where country is not null
),
order_lines as (
    select
        o.channel,
        o.sku,
        o.shipment_id,
        o.quantity_sold,
        o.quantity_returned,
        o.gross_sale,
        o.taxes,
        o.net_sales,
        o.created_at
    from `{project}.production.fct_sale_order_line` o
    inner join products p on o.sku = p.sku
    inner join shipments s on o.shipment_id = s.shipment_id
    where o.quantity_returned <= o.quantity_sold
        and o.net_sales >= 0
        and o.quantity_sold > 0
),
fct_sales_enriched as (
    select
        order_lines.channel,
        order_lines.sku,
        products.cost,
        products.category,
        order_lines.quantity_sold,
        order_lines.quantity_returned,
        order_lines.gross_sale,
        order_lines.taxes,
        order_lines.net_sales,
        order_lines.created_at,
        shipments.country,
        safe_divide(
            order_lines.net_sales,
            sum(order_lines.net_sales) over (partition by order_lines.shipment_id)
        ) * shipments.shipping_cost as allocated_shipping_cost
    from order_lines
    inner join products on order_lines.sku = products.sku
    inner join shipments on order_lines.shipment_id = shipments.shipment_id
)
"""

CHANNEL_PERFORMANCE_QUERY = f"""
select *
from `{{project}}.{DATAMART_DATASET}.mart_channel_performance_monthly`
order by period_month, channel
"""

CHANNEL_PERFORMANCE_FALLBACK_QUERY = (
    "with "
    + FCT_SALES_ENRICHED_INLINE_CTES
    + """,
sales as (
    select
        channel,
        date(date_trunc(created_at, month)) as period_month,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost
    from fct_sales_enriched
),
line_agg as (
    select
        period_month,
        channel,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost
    from sales
    group by period_month, channel
),
combined as (
    select
        period_month,
        channel,
        gross_sale,
        taxes,
        net_sales,
        quantity_sold,
        quantity_returned,
        product_cost,
        shipping_cost,
        net_sales - product_cost - shipping_cost as contribution_margin
    from line_agg
),
with_kpis as (
    select
        period_month,
        channel,
        gross_sale,
        taxes,
        net_sales,
        quantity_sold,
        quantity_returned,
        product_cost,
        shipping_cost,
        contribution_margin,
        safe_divide(quantity_returned, quantity_sold) as return_rate,
        safe_divide(net_sales, quantity_sold) as avg_order_value,
        safe_divide(contribution_margin, net_sales) as contribution_margin_pct,
        safe_divide(
            net_sales,
            sum(net_sales) over (partition by period_month)
        ) as pct_of_total_net_sales
    from combined
),
with_yoy as (
    select
        current_period.period_month,
        current_period.channel,
        current_period.gross_sale,
        current_period.taxes,
        current_period.net_sales,
        current_period.quantity_sold,
        current_period.quantity_returned,
        current_period.product_cost,
        current_period.shipping_cost,
        current_period.contribution_margin,
        current_period.return_rate,
        current_period.avg_order_value,
        current_period.contribution_margin_pct,
        current_period.pct_of_total_net_sales,
        prior_period.net_sales as net_sales_prior_year,
        prior_period.return_rate as return_rate_prior_year,
        prior_period.contribution_margin_pct as contribution_margin_pct_prior_year,
        safe_divide(
            current_period.net_sales - prior_period.net_sales,
            prior_period.net_sales
        ) as net_sales_yoy_pct,
        current_period.return_rate - prior_period.return_rate as return_rate_yoy_pp,
        current_period.contribution_margin_pct
            - prior_period.contribution_margin_pct as contribution_margin_pct_yoy_pp
    from with_kpis as current_period
    left join with_kpis as prior_period
        on current_period.channel = prior_period.channel
        and prior_period.period_month = date_sub(
            current_period.period_month,
            interval 12 month
        )
)
select * from with_yoy
order by period_month, channel
"""
)

_CHANNEL_GRAIN_FALLBACK = """
with """ + FCT_SALES_ENRICHED_INLINE_CTES + """,
sales as (
    select
        channel,
        {period_expr} as period_date,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost
    from fct_sales_enriched
),
line_agg as (
    select
        period_date,
        channel,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost
    from sales
    group by period_date, channel
)
select
    period_date,
    channel,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    net_sales - product_cost - shipping_cost as contribution_margin,
    safe_divide(quantity_returned, quantity_sold) as return_rate,
    safe_divide(net_sales, quantity_sold) as avg_order_value,
    safe_divide(net_sales - product_cost - shipping_cost, net_sales) as contribution_margin_pct,
    safe_divide(
        net_sales,
        sum(net_sales) over (partition by period_date)
    ) as pct_of_total_net_sales
from line_agg
order by period_date, channel
"""

_CHANNEL_GRAIN_QUERY = f"""
with sales as (
    select
        channel,
        {{period_expr}} as period_date,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost
    from {FCT_SALES_ENRICHED_TABLE}
),
line_agg as (
    select
        period_date,
        channel,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost
    from sales
    group by period_date, channel
)
select
    period_date,
    channel,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    net_sales - product_cost - shipping_cost as contribution_margin,
    safe_divide(quantity_returned, quantity_sold) as return_rate,
    safe_divide(net_sales, quantity_sold) as avg_order_value,
    safe_divide(net_sales - product_cost - shipping_cost, net_sales) as contribution_margin_pct,
    safe_divide(
        net_sales,
        sum(net_sales) over (partition by period_date)
    ) as pct_of_total_net_sales
from line_agg
order by period_date, channel
"""

CHANNEL_DAILY_QUERY = _CHANNEL_GRAIN_QUERY.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, day))",
)
CHANNEL_WEEKLY_QUERY = _CHANNEL_GRAIN_QUERY.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, week(monday)))",
)
CHANNEL_DAILY_FALLBACK_QUERY = _CHANNEL_GRAIN_FALLBACK.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, day))",
)
CHANNEL_WEEKLY_FALLBACK_QUERY = _CHANNEL_GRAIN_FALLBACK.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, week(monday)))",
)

_COUNTRY_GRAIN_FALLBACK = """
with """ + FCT_SALES_ENRICHED_INLINE_CTES + """,
sales as (
    select
        channel,
        country,
        {period_expr} as period_date,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost
    from fct_sales_enriched
),
line_agg as (
    select
        period_date,
        channel,
        country,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost
    from sales
    group by period_date, channel, country
)
select
    period_date,
    channel,
    country,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    net_sales - product_cost - shipping_cost as contribution_margin,
    safe_divide(quantity_returned, quantity_sold) as return_rate,
    safe_divide(net_sales, quantity_sold) as avg_order_value,
    safe_divide(net_sales - product_cost - shipping_cost, net_sales) as contribution_margin_pct,
    safe_divide(
        net_sales,
        sum(net_sales) over (partition by period_date, channel)
    ) as pct_of_channel_net_sales
from line_agg
order by period_date, channel, country
"""

_COUNTRY_GRAIN_QUERY = f"""
with sales as (
    select
        channel,
        country,
        {{period_expr}} as period_date,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost
    from {FCT_SALES_ENRICHED_TABLE}
),
line_agg as (
    select
        period_date,
        channel,
        country,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost
    from sales
    group by period_date, channel, country
)
select
    period_date,
    channel,
    country,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    net_sales - product_cost - shipping_cost as contribution_margin,
    safe_divide(quantity_returned, quantity_sold) as return_rate,
    safe_divide(net_sales, quantity_sold) as avg_order_value,
    safe_divide(net_sales - product_cost - shipping_cost, net_sales) as contribution_margin_pct,
    safe_divide(
        net_sales,
        sum(net_sales) over (partition by period_date, channel)
    ) as pct_of_channel_net_sales
from line_agg
order by period_date, channel, country
"""

COUNTRY_DAILY_QUERY = _COUNTRY_GRAIN_QUERY.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, day))",
)
COUNTRY_WEEKLY_QUERY = _COUNTRY_GRAIN_QUERY.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, week(monday)))",
)
COUNTRY_DAILY_FALLBACK_QUERY = _COUNTRY_GRAIN_FALLBACK.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, day))",
)
COUNTRY_WEEKLY_FALLBACK_QUERY = _COUNTRY_GRAIN_FALLBACK.format(
    project="{project}",
    period_expr="date(date_trunc(created_at, week(monday)))",
)

COUNTRY_PERFORMANCE_QUERY = f"""
select
    period_month,
    channel,
    country,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    contribution_margin,
    return_rate,
    avg_order_value,
    contribution_margin_pct,
    pct_of_channel_net_sales
from `{{project}}.{DATAMART_DATASET}.mart_country_performance_monthly`
order by period_month, channel, country
"""

COUNTRY_PERFORMANCE_FALLBACK_QUERY = (
    "with "
    + FCT_SALES_ENRICHED_INLINE_CTES
    + """,
sales as (
    select
        channel,
        country,
        date(date_trunc(created_at, month)) as period_month,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost
    from fct_sales_enriched
),
line_agg as (
    select
        period_month,
        channel,
        country,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost
    from sales
    group by period_month, channel, country
),
combined as (
    select
        period_month,
        channel,
        country,
        gross_sale,
        taxes,
        net_sales,
        quantity_sold,
        quantity_returned,
        product_cost,
        shipping_cost,
        net_sales - product_cost - shipping_cost as contribution_margin
    from line_agg
)
select
    period_month,
    channel,
    country,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    contribution_margin,
    safe_divide(quantity_returned, quantity_sold) as return_rate,
    safe_divide(net_sales, quantity_sold) as avg_order_value,
    safe_divide(contribution_margin, net_sales) as contribution_margin_pct,
    safe_divide(
        net_sales,
        sum(net_sales) over (partition by period_month, channel)
    ) as pct_of_channel_net_sales
from combined
order by period_month, channel, country
"""
)

WHOLESALE_PERFORMANCE_QUERY = f"""
select
    period_month,
    country,
    category,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    contribution_margin,
    return_rate,
    avg_order_value,
    contribution_margin_pct,
    pct_of_wholesale_net_sales
from `{{project}}.{DATAMART_DATASET}.mart_wholesale_performance_monthly`
order by period_month, country, category
"""

WHOLESALE_PERFORMANCE_FALLBACK_QUERY = (
    "with "
    + FCT_SALES_ENRICHED_INLINE_CTES
    + """,
sales as (
    select
        country,
        category,
        date(date_trunc(created_at, month)) as period_month,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost
    from fct_sales_enriched
    where lower(channel) = 'wholesale'
),
line_agg as (
    select
        period_month,
        country,
        category,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost
    from sales
    group by period_month, country, category
),
combined as (
    select
        period_month,
        country,
        category,
        gross_sale,
        taxes,
        net_sales,
        quantity_sold,
        quantity_returned,
        product_cost,
        shipping_cost,
        net_sales - product_cost - shipping_cost as contribution_margin
    from line_agg
)
select
    period_month,
    country,
    category,
    gross_sale,
    taxes,
    net_sales,
    quantity_sold,
    quantity_returned,
    product_cost,
    shipping_cost,
    contribution_margin,
    safe_divide(quantity_returned, quantity_sold) as return_rate,
    safe_divide(net_sales, quantity_sold) as avg_order_value,
    safe_divide(contribution_margin, net_sales) as contribution_margin_pct,
    safe_divide(
        net_sales,
        sum(net_sales) over (partition by period_month)
    ) as pct_of_wholesale_net_sales
from combined
order by period_month, country, category
"""
)

DATA_QUALITY_SUMMARY_QUERY = """
with order_lines as (
    select * from `{project}.production.fct_sale_order_line`
),
products as (
    select * from `{project}.production.dim_product`
),
shipments as (
    select * from `{project}.production.fct_shipment`
),
order_line_total as (
    select count(*) as total_rows from order_lines
),
shipment_total as (
    select count(*) as total_rows from shipments
),
product_total as (
    select count(*) as total_rows from products
),
checks as (
    select
        'fct_sale_order_line' as source_table,
        'orphan_sku' as issue_type,
        'SKU not found in dim_product' as issue_description,
        'High' as severity,
        count(*) as row_count
    from order_lines as o
    left join products as p on o.sku = p.sku
    where p.sku is null

    union all

    select
        'fct_sale_order_line',
        'orphan_shipment',
        'shipment_id not found in fct_shipment',
        'High',
        count(*)
    from order_lines as o
    left join shipments as s on o.shipment_id = s.shipment_id
    where s.shipment_id is null

    union all

    select
        'fct_sale_order_line',
        'returns_exceed_sold',
        'quantity_returned exceeds quantity_sold',
        'Medium',
        count(*)
    from order_lines
    where quantity_returned > quantity_sold

    union all

    select
        'fct_sale_order_line',
        'negative_net_sales',
        'net_sales is negative',
        'Medium',
        count(*)
    from order_lines
    where net_sales < 0

    union all

    select
        'fct_sale_order_line',
        'zero_quantity_sold',
        'quantity_sold is zero',
        'Low',
        count(*)
    from order_lines
    where quantity_sold = 0

    union all

    select
        'fct_shipment',
        'null_country',
        'country is null',
        'High',
        count(*)
    from shipments
    where country is null

    union all

    select
        'dim_product',
        'null_cost',
        'product cost is null',
        'Medium',
        count(*)
    from products
    where cost is null
)
select
    c.source_table,
    c.issue_type,
    c.issue_description,
    c.severity,
    c.row_count,
    safe_divide(
        c.row_count,
        case c.source_table
            when 'fct_sale_order_line' then (select total_rows from order_line_total)
            when 'fct_shipment' then (select total_rows from shipment_total)
            else (select total_rows from product_total)
        end
    ) as pct_of_table
from checks as c
order by
    c.row_count desc,
    case c.severity when 'High' then 1 when 'Medium' then 2 else 3 end,
    c.issue_type
"""

_ORDER_LINE_DETAIL_COLUMNS = """
    o.channel,
    o.sku,
    o.shipment_id,
    o.quantity_sold,
    o.quantity_returned,
    o.gross_sale,
    o.net_sales,
    o.created_at
"""

DATA_QUALITY_ORPHAN_SKU_QUERY = """
with order_lines as (
    select * from `{project}.production.fct_sale_order_line`
),
products as (
    select * from `{project}.production.dim_product`
)
select
""" + _ORDER_LINE_DETAIL_COLUMNS + """
from order_lines as o
left join products as p on o.sku = p.sku
where p.sku is null
order by o.created_at desc
limit {limit}
"""

DATA_QUALITY_ORPHAN_SHIPMENT_QUERY = """
with order_lines as (
    select * from `{project}.production.fct_sale_order_line`
),
shipments as (
    select * from `{project}.production.fct_shipment`
)
select
""" + _ORDER_LINE_DETAIL_COLUMNS + """
from order_lines as o
left join shipments as s on o.shipment_id = s.shipment_id
where s.shipment_id is null
order by o.created_at desc
limit {limit}
"""

DATA_QUALITY_RETURNS_EXCEED_SOLD_QUERY = """
with order_lines as (
    select * from `{project}.production.fct_sale_order_line`
)
select
""" + _ORDER_LINE_DETAIL_COLUMNS + """
from order_lines as o
where o.quantity_returned > o.quantity_sold
order by o.quantity_returned - o.quantity_sold desc, o.created_at desc
limit {limit}
"""

DATA_QUALITY_NEGATIVE_NET_SALES_QUERY = """
with order_lines as (
    select * from `{project}.production.fct_sale_order_line`
)
select
""" + _ORDER_LINE_DETAIL_COLUMNS + """
from order_lines as o
where o.net_sales < 0
order by o.net_sales asc, o.created_at desc
limit {limit}
"""

DATA_QUALITY_ZERO_QUANTITY_SOLD_QUERY = """
with order_lines as (
    select * from `{project}.production.fct_sale_order_line`
)
select
""" + _ORDER_LINE_DETAIL_COLUMNS + """
from order_lines as o
where o.quantity_sold = 0
order by o.created_at desc
limit {limit}
"""

DATA_QUALITY_NULL_COUNTRY_QUERY = """
with shipments as (
    select * from `{project}.production.fct_shipment`
)
select
    s.shipment_id,
    s.shipping_method,
    s.shipping_cost,
    s.country
from shipments as s
where s.country is null
order by s.shipment_id
limit {limit}
"""

DATA_QUALITY_NULL_COST_QUERY = """
with products as (
    select * from `{project}.production.dim_product`
)
select
    p.sku,
    p.name,
    p.category,
    p.base_price,
    p.cost
from products as p
where p.cost is null
order by p.sku
limit {limit}
"""

DATA_QUALITY_DETAIL_QUERIES = {
    "orphan_sku": DATA_QUALITY_ORPHAN_SKU_QUERY,
    "orphan_shipment": DATA_QUALITY_ORPHAN_SHIPMENT_QUERY,
    "returns_exceed_sold": DATA_QUALITY_RETURNS_EXCEED_SOLD_QUERY,
    "negative_net_sales": DATA_QUALITY_NEGATIVE_NET_SALES_QUERY,
    "zero_quantity_sold": DATA_QUALITY_ZERO_QUANTITY_SOLD_QUERY,
    "null_country": DATA_QUALITY_NULL_COUNTRY_QUERY,
    "null_cost": DATA_QUALITY_NULL_COST_QUERY,
}
