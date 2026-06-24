with source as (

    select * from {{ source('production', 'fct_shipment') }}

),

renamed as (

    select
        shipment_id,
        shipping_method,
        shipping_cost,
        country

    from source
    where country is not null

)

select * from renamed
