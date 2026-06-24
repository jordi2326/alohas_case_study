with sales as (

    select
        channel,
        date(date_trunc(created_at, day)) as period_day,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        cost,
        allocated_shipping_cost

    from {{ ref('fct_sales_enriched') }}

),

line_agg as (

    select
        period_day,
        channel,
        sum(gross_sale) as gross_sale,
        sum(taxes) as taxes,
        sum(net_sales) as net_sales,
        sum(quantity_sold) as quantity_sold,
        sum(quantity_returned) as quantity_returned,
        sum(quantity_sold * cost) as product_cost,
        sum(coalesce(allocated_shipping_cost, 0)) as shipping_cost

    from sales
    group by
        period_day,
        channel

)

select
    period_day,
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
    safe_divide(net_sales - product_cost - shipping_cost, net_sales)
        as contribution_margin_pct,
    safe_divide(
        net_sales,
        sum(net_sales) over (partition by period_day)
    ) as pct_of_total_net_sales

from line_agg
