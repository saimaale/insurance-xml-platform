-- ---------------------------------------------------------------------------
-- stg_br_policy_transaction
-- Root node — one row per XML file.
-- Carries policy_transaction_sk (root surrogate key) downstream.
-- ---------------------------------------------------------------------------
select
    policy_transaction_sk,
    transaction_id,
    policy_term_count,
    rb_correlation_service_id,
    transaction_seq_num,
    endorsement_type_code,
    endorsement_type_value,
    transaction_type_code,
    transaction_type_value,
    source_file_name,
    cast(source_load_ts as timestamp)   as source_load_ts
from {{ source('bronze', 'br_policy_transaction') }}
