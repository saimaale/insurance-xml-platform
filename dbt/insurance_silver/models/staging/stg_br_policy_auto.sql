-- ---------------------------------------------------------------------------
-- stg_br_policy_auto
-- PolicyAuto — one row per XML file.
-- Carries policy_auto_sk downstream (critical FK for vehicle + jurisdiction).
-- ---------------------------------------------------------------------------
select
    policy_auto_sk,
    policy_transaction_policy_sk,
    transaction_id,
    policy_number,
    greatest_driver_number,
    greatest_vehicle_number,
    total_number_of_drivers,
    total_number_of_vehicles,
    private_passenger_vehicle_count,
    source_file_name,
    cast(source_load_ts as timestamp)   as source_load_ts
from {{ source('bronze', 'br_policy_auto') }}
