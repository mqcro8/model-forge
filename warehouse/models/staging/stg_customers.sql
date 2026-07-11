with

source as (
    select * from {{ ref('customers') }}
),

renamed as (
    select
        customer_id,
        first_name,
        last_name,
        email,
        country,
        signup_date,
        is_active
    from source
)

select * from renamed