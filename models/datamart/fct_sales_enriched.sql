with order_lines as (

    select
        channel,
        sku,
        shipment_id,
        quantity_sold,
        quantity_returned,
        gross_sale,
        taxes,
        net_sales,
        created_at

    from {{ ref('gold_fct_sale_order_line') }}

),

products as (

    select
        sku,
        name,
        category,
        base_price,
        cost

    from {{ ref('gold_dim_product') }}

),

shipments as (

    select
        shipment_id,
        shipping_method,
        shipping_cost,
        country

    from {{ ref('gold_fct_shipment') }}

),

joined as (

    select
        order_lines.channel,
        order_lines.sku,
        products.name as product_name,
        products.category,
        products.base_price,
        products.cost,
        order_lines.shipment_id,
        shipments.shipping_method,
        shipments.shipping_cost,
        shipments.country,
        order_lines.quantity_sold,
        order_lines.quantity_returned,
        order_lines.gross_sale,
        order_lines.taxes,
        order_lines.net_sales,
        order_lines.created_at,
        safe_divide(
            order_lines.net_sales,
            sum(order_lines.net_sales) over (partition by order_lines.shipment_id)
        ) * shipments.shipping_cost as allocated_shipping_cost

    from order_lines
    inner join products
        on order_lines.sku = products.sku
    inner join shipments
        on order_lines.shipment_id = shipments.shipment_id

)

select * from joined
