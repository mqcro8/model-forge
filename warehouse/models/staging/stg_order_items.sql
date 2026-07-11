with

source as (
    select * from {{ ref('order_items') }}
),

renamed as (
    select
        order_item_id,
        order_id,
        product_name,
        quantity,
        unit_price
    from source
)

select * from renamed