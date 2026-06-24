with source as (

    select * from {{ source('production', 'dim_product') }}

),

renamed as (

    select
        sku,
        name,
        category,
        base_price,
        cost

    from source
    where cost is not null

)

select * from renamed
