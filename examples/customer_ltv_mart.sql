

with

c as (
    select


        customer_id as customer_id,
        first_name as customer_name,
        country as country
    from {{ ref('stg_customers') }}
),

o as (
    select


        total_amount as total_spend,
        order_id as order_count,
        customer_id
    from {{ ref('stg_orders') }}
    where 
        order_status = 'completed'
)

select

        c.customer_id as customer_id,
        c.customer_name as customer_name,
        c.country as country,
        sum(o.total_spend) as total_spend,
        count(o.order_count) as order_count
    from c
    left join o on c.customer_id = o.customer_id
    group by
        1,
        2,
        3
