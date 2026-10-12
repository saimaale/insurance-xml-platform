-- ---------------------------------------------------------------------------
-- stg_br_policy_transaction_policy
-- PolicyTransactionPolicy — one row per XML file.
-- Carries policy_transaction_policy_sk and policy_transaction_sk downstream.
-- ---------------------------------------------------------------------------
select
    policy_transaction_policy_sk,
    policy_transaction_sk,
    transaction_id,
    policy_number,
    agency_legal_name,
    agency_number,
    naic_code,
    quote_number,
    inception_date,
    policy_effective_date,
    policy_expiration_date,
    term_effective_date,
    term_expiration_date,
    transaction_effective_date,
    transaction_completed_date,
    primary_risk_state_code,
    primary_risk_state_value,
    source_file_name,
    cast(source_load_ts as timestamp)   as source_load_ts
from {{ source('bronze', 'br_policy_transaction_policy') }}
