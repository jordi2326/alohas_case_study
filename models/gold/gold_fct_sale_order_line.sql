with source as (

    select * from {{ source('production', 'fct_sale_order_line') }}

),

valid_products as (

    select sku from {{ ref('gold_dim_product') }}

),

valid_shipments as (

    select shipment_id from {{ ref('gold_fct_shipment') }}

),

filtered as (

    select
        source.channel,
        source.sku,
        source.shipment_id,
        source.quantity_sold,
        source.quantity_returned,
        source.gross_sale,
        source.taxes,
        source.net_sales,
        source.created_at

    from source
    inner join valid_products
        on source.sku = valid_products.sku
    inner join valid_shipments
        on source.shipment_id = valid_shipments.shipment_id
    where source.quantity_returned <= source.quantity_sold
        and source.net_sales >= 0
        and source.quantity_sold > 0

)

select * from filtered
