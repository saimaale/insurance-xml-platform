-- ---------------------------------------------------------------------------
-- sl_policy  (Silver — Incremental SCD Type 2)
--
-- Run modes:
--
--   Historical  (full rebuild — wipe Silver first):
--     dbt run --select silver --full-refresh --profiles-dir .
--
--   Transactional  (default — new transactions via watermark):
--     dbt run --select silver --profiles-dir .
--
--   Reprocess  (date-range backfill — re-merges a window of transactions):
--     dbt run --select silver \
--             --vars '{"load_type": "reprocess", "start_date": "2024-01-01", "end_date": "2024-06-30"}' \
--             --profiles-dir .
--
-- Grain        : (policy_number, policy_term_count, transaction_seq_num)
-- SCD2 key     : (policy_number, policy_term_count)
-- Current rows : is_current = true
-- ---------------------------------------------------------------------------
{{ config(
    materialized          = 'incremental',
    incremental_strategy  = 'merge',
    unique_key            = ['policy_number', 'policy_term_count', 'transaction_seq_num'],
    table_type            = 'iceberg',
    on_schema_change      = 'sync_all_columns',
    s3_data_dir           = 's3://ins-xml-dev-silver/dbt/sl_policy/'
) }}

{% set load_type = var('load_type', 'transactional') %}

-- ── Step 1: Flatten all Bronze policy staging into one row per transaction ──
with all_bronze as (
    select
        txn.policy_transaction_sk,
        ptp.policy_transaction_policy_sk,
        auto.policy_auto_sk,
        juris.policy_auto_jurisdiction_sk,
        ptp.policy_number,
        txn.policy_term_count,
        txn.transaction_seq_num,
        ptp.transaction_id,
        txn.transaction_type_code,
        txn.transaction_type_value,
        txn.endorsement_type_code,
        txn.endorsement_type_value,
        ptp.agency_legal_name,
        ptp.agency_number,
        ptp.naic_code,
        ptp.quote_number,
        ptp.inception_date,
        ptp.policy_effective_date,
        ptp.policy_expiration_date,
        ptp.term_effective_date,
        ptp.term_expiration_date,
        ptp.transaction_effective_date,
        ptp.transaction_completed_date,
        ptp.primary_risk_state_code,
        ptp.primary_risk_state_value,
        auto.total_number_of_vehicles,
        auto.total_number_of_drivers,
        auto.private_passenger_vehicle_count,
        juris.jurisdiction_state_code,
        juris.garaging_state,
        juris.city_name,
        juris.zip_code,
        txn.source_file_name,
        txn.source_load_ts,
        -- SCD2 hash: business attributes only, no transaction flags
        to_hex(md5(to_utf8(concat(
            coalesce(ptp.primary_risk_state_code,                   ''),
            coalesce(ptp.policy_effective_date,                     ''),
            coalesce(ptp.policy_expiration_date,                    ''),
            coalesce(ptp.agency_legal_name,                         ''),
            coalesce(cast(auto.total_number_of_vehicles as varchar),''),
            coalesce(juris.zip_code,                                '')
        )))) as row_hash
    from {{ ref('stg_br_policy_transaction') }}        txn
    join {{ ref('stg_br_policy_transaction_policy') }} ptp
        on ptp.policy_transaction_sk         = txn.policy_transaction_sk
    join {{ ref('stg_br_policy_auto') }}               auto
        on auto.policy_transaction_policy_sk = ptp.policy_transaction_policy_sk
    left join {{ ref('stg_br_policy_auto_jurisdiction') }} juris
        on juris.policy_auto_sk              = auto.policy_auto_sk
),

{% if is_incremental() %}

{% if load_type == 'reprocess' %}

-- ── REPROCESS PATH ──────────────────────────────────────────────────────────
-- Re-merges all Bronze transactions whose effective date falls in the given
-- window. Use when source data was corrected for a known historical period.
new_transactions as (
    select b.*
    from all_bronze b
    where cast(b.transaction_effective_date as date) >= cast('{{ var("start_date") }}' as date)
      and cast(b.transaction_effective_date as date) <= cast('{{ var("end_date") }}' as date)
),

{% else %}

-- ── TRANSACTIONAL PATH ──────────────────────────────────────────────────────
-- Find the last processed transaction_seq_num per (policy, term) in Silver
watermark as (
    select
        policy_number,
        policy_term_count,
        max(transaction_seq_num) as max_seq
    from {{ this }}
    group by policy_number, policy_term_count
),

-- Only Bronze transactions not yet in Silver
new_transactions as (
    select b.*
    from all_bronze b
    left join watermark w
        on  w.policy_number     = b.policy_number
        and w.policy_term_count = b.policy_term_count
    where w.max_seq is null                      -- brand new policy/term
       or b.transaction_seq_num > w.max_seq      -- new transaction for existing term
),

{% endif %}

-- Expire current Silver records where the new transaction has a different hash
records_to_expire as (
    select
        s.policy_transaction_sk,
        s.policy_transaction_policy_sk,
        s.policy_auto_sk,
        s.policy_auto_jurisdiction_sk,
        s.policy_number,
        s.policy_term_count,
        s.transaction_seq_num,          -- original seq_num → MERGE matches and UPDATEs this row
        s.transaction_id,
        s.transaction_type_code,
        s.transaction_type_value,
        s.endorsement_type_code,
        s.endorsement_type_value,
        s.agency_legal_name,
        s.agency_number,
        s.naic_code,
        s.quote_number,
        s.inception_date,
        s.policy_effective_date,
        s.policy_expiration_date,
        s.term_effective_date,
        s.term_expiration_date,
        s.transaction_effective_date,
        s.transaction_completed_date,
        s.primary_risk_state_code,
        s.primary_risk_state_value,
        s.total_number_of_vehicles,
        s.total_number_of_drivers,
        s.private_passenger_vehicle_count,
        s.jurisdiction_state_code,
        s.garaging_state,
        s.city_name,
        s.zip_code,
        s.row_hash,
        false                                              as is_current,
        n.transaction_effective_date                       as effective_to_dt,
        s.effective_from_dt,
        s.source_file_name,
        s.source_load_ts,
        cast(current_timestamp as timestamp)               as dbt_updated_at
    from {{ this }} s
    join new_transactions n
        on  n.policy_number     = s.policy_number
        and n.policy_term_count = s.policy_term_count
    where s.is_current = true
      and s.row_hash  != n.row_hash       -- only expire if something actually changed
),

-- New active records to insert (one per new transaction)
new_records as (
    select
        policy_transaction_sk,
        policy_transaction_policy_sk,
        policy_auto_sk,
        policy_auto_jurisdiction_sk,
        policy_number,
        policy_term_count,
        transaction_seq_num,
        transaction_id,
        transaction_type_code,
        transaction_type_value,
        endorsement_type_code,
        endorsement_type_value,
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
        total_number_of_vehicles,
        total_number_of_drivers,
        private_passenger_vehicle_count,
        jurisdiction_state_code,
        garaging_state,
        city_name,
        zip_code,
        row_hash,
        true                                               as is_current,
        null                                               as effective_to_dt,
        transaction_effective_date                         as effective_from_dt,
        source_file_name,
        source_load_ts,
        cast(current_timestamp as timestamp)               as dbt_updated_at
    from new_transactions
),

final as (
    select * from records_to_expire
    union all
    select * from new_records
)

{% else %}

-- ── HISTORICAL PATH ──────────────────────────────────────────────────────────
-- Full rebuild: window functions detect changes across all transactions
hashed as (
    select
        *,
        lag(row_hash) over (
            partition by policy_number, policy_term_count
            order by transaction_seq_num
        ) as prev_hash
    from all_bronze
),

new_versions as (
    select * from hashed
    where prev_hash is null          -- first transaction for this policy/term
       or row_hash != prev_hash      -- something changed
),

final as (
    select
        policy_transaction_sk,
        policy_transaction_policy_sk,
        policy_auto_sk,
        policy_auto_jurisdiction_sk,
        policy_number,
        policy_term_count,
        transaction_seq_num,
        transaction_id,
        transaction_type_code,
        transaction_type_value,
        endorsement_type_code,
        endorsement_type_value,
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
        total_number_of_vehicles,
        total_number_of_drivers,
        private_passenger_vehicle_count,
        jurisdiction_state_code,
        garaging_state,
        city_name,
        zip_code,
        row_hash,
        case
            when lead(transaction_effective_date) over (
                partition by policy_number, policy_term_count
                order by transaction_seq_num
            ) is null then true
            else false
        end                                                as is_current,
        lead(transaction_effective_date) over (
            partition by policy_number, policy_term_count
            order by transaction_seq_num
        )                                                  as effective_to_dt,
        transaction_effective_date                         as effective_from_dt,
        source_file_name,
        source_load_ts,
        cast(current_timestamp as timestamp)               as dbt_updated_at
    from new_versions
)

{% endif %}

select * from final
