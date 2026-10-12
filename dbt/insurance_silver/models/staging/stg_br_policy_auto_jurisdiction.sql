-- ---------------------------------------------------------------------------
-- stg_br_policy_auto_jurisdiction
-- PolicyAutoJurisdiction joined to PolicyAutoLocation via surrogate key.
-- One row per XML file (1:1 with PolicyAuto).
-- ---------------------------------------------------------------------------
select
    j.policy_auto_jurisdiction_sk,
    j.policy_auto_sk,
    j.transaction_id,
    j.policy_number,
    -- StateCode (id/code/value)
    j.state_code_code                       as jurisdiction_state_code,
    j.state_code_value                      as jurisdiction_state_value,
    -- Location fields
    l.city_name,
    l.delivery_address,
    l.state                                 as garaging_state,
    l.zip_code,
    j.source_file_name,
    cast(j.source_load_ts as timestamp)     as source_load_ts
from {{ source('bronze', 'br_policy_auto_jurisdiction') }} j
left join {{ source('bronze', 'br_policy_auto_location') }} l
    on l.policy_auto_jurisdiction_sk = j.policy_auto_jurisdiction_sk
