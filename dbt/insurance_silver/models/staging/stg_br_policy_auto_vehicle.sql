-- ---------------------------------------------------------------------------
-- stg_br_policy_auto_vehicle
-- PolicyAutoVehicle — one row per vehicle per transaction.
-- covered_item_identifier is the stable business key for a vehicle.
-- ---------------------------------------------------------------------------
select
    policy_auto_vehicle_sk,
    policy_auto_sk,
    transaction_id,
    policy_number,
    covered_item_number,
    covered_item_identifier,
    vehicle_change_type_code,
    busines_operation_group,
    vehicle_type,
    vehicle_make,
    vehicle_model,
    vehicle_model_year,
    source_file_name,
    cast(source_load_ts as timestamp)   as source_load_ts
from {{ source('bronze', 'br_policy_auto_vehicle') }}
