with sales as (

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

    from {{ ref('fct_sales_enriched') }}
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
    group by
        period_month,
        country,
        category

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

),

with_kpis as (

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

),

with_yoy as (

    select
        current_period.period_month,
        current_period.country,
        current_period.category,
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
        current_period.pct_of_wholesale_net_sales,
        prior_period.net_sales as net_sales_prior_year,
        prior_period.return_rate as return_rate_prior_year,
        safe_divide(
            current_period.net_sales - prior_period.net_sales,
            prior_period.net_sales
        ) as net_sales_yoy_pct,
        current_period.return_rate - prior_period.return_rate as return_rate_yoy_pp

    from with_kpis as current_period
    left join with_kpis as prior_period
        on current_period.country = prior_period.country
        and current_period.category = prior_period.category
        and prior_period.period_month = date_sub(
            current_period.period_month,
            interval 12 month
        )

)

select * from with_yoy
