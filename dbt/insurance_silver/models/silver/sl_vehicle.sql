-- ---------------------------------------------------------------------------
-- sl_vehicle  (Silver — Incremental SCD Type 2)
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
-- Grain        : (policy_number, policy_term_count, covered_item_identifier,
--                transaction_seq_num)
-- SCD2 key     : (policy_number, policy_term_count, covered_item_identifier)
-- Current rows : is_current = true
-- ---------------------------------------------------------------------------
{{ config(
    materialized          = 'incremental',
    incremental_strategy  = 'merge',
    unique_key            = ['policy_number', 'policy_term_count',
                             'covered_item_identifier', 'transaction_seq_num'],
    table_type            = 'iceberg',
    on_schema_change      = 'sync_all_columns',
    s3_data_dir           = 's3://ins-xml-dev-silver/dbt/sl_vehicle/'
) }}

{% set load_type = var('load_type', 'transactional') %}

-- ── Step 1: Flatten Bronze vehicle + policy context ─────────────────────────
with all_bronze as (
    select
        v.policy_auto_vehicle_sk,
        v.policy_auto_sk,
        v.transaction_id,
        v.policy_number,
        v.covered_item_number,
        v.covered_item_identifier,
        v.vehicle_change_type_code,
        v.busines_operation_group,
        v.vehicle_type,
        v.vehicle_make,
        v.vehicle_model,
        v.vehicle_model_year,
        -- policy context joined from sl_policy (all versions, match on Bronze SK)
        p.policy_term_count,
        p.transaction_seq_num,
        p.primary_risk_state_code,
        p.policy_effective_date,
        p.policy_expiration_date,
        p.garaging_state,
        p.zip_code,
        p.transaction_effective_date,
        v.source_file_name,
        v.source_load_ts,
        -- SCD2 hash
        to_hex(md5(to_utf8(concat(
            coalesce(v.vehicle_change_type_code,                    ''),
            coalesce(v.vehicle_make,                                ''),
            coalesce(v.vehicle_model,                               ''),
            coalesce(cast(v.vehicle_model_year as varchar),         ''),
            coalesce(v.vehicle_type,                                ''),
            coalesce(v.busines_operation_group,                     '')
        )))) as row_hash
    from {{ ref('stg_br_policy_auto_vehicle') }} v
    -- join ALL sl_policy versions (not just current) to get correct context per transaction
    join {{ ref('sl_policy') }} p
        on p.policy_auto_sk = v.policy_auto_sk
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
watermark as (
    select
        policy_number,
        policy_term_count,
        covered_item_identifier,
        max(transaction_seq_num) as max_seq
    from {{ this }}
    group by policy_number, policy_term_count, covered_item_identifier
),

new_transactions as (
    select b.*
    from all_bronze b
    left join watermark w
        on  w.policy_number           = b.policy_number
        and w.policy_term_count       = b.policy_term_count
        and w.covered_item_identifier = b.covered_item_identifier
    where w.max_seq is null
       or b.transaction_seq_num > w.max_seq
),

{% endif %}

records_to_expire as (
    select
        s.policy_auto_vehicle_sk,
        s.policy_auto_sk,
        s.transaction_id,
        s.policy_number,
        s.policy_term_count,
        s.covered_item_number,
        s.covered_item_identifier,
        s.vehicle_change_type_code,
        s.busines_operation_group,
        s.vehicle_type,
        s.vehicle_make,
        s.vehicle_model,
        s.vehicle_model_year,
        s.primary_risk_state_code,
        s.policy_effective_date,
        s.policy_expiration_date,
        s.garaging_state,
        s.zip_code,
        s.transaction_seq_num,
        s.row_hash,
        false                                              as is_current,
        n.transaction_effective_date                       as effective_to_dt,
        s.effective_from_dt,
        s.source_file_name,
        s.source_load_ts,
        cast(current_timestamp as timestamp)               as dbt_updated_at
    from {{ this }} s
    join new_transactions n
        on  n.policy_number           = s.policy_number
        and n.policy_term_count       = s.policy_term_count
        and n.covered_item_identifier = s.covered_item_identifier
    where s.is_current = true
      and s.row_hash  != n.row_hash
),

new_records as (
    select
        policy_auto_vehicle_sk,
        policy_auto_sk,
        transaction_id,
        policy_number,
        policy_term_count,
        covered_item_number,
        covered_item_identifier,
        vehicle_change_type_code,
        busines_operation_group,
        vehicle_type,
        vehicle_make,
        vehicle_model,
        vehicle_model_year,
        primary_risk_state_code,
        policy_effective_date,
        policy_expiration_date,
        garaging_state,
        zip_code,
        transaction_seq_num,
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
hashed as (
    select
        *,
        lag(row_hash) over (
            partition by policy_number, policy_term_count, covered_item_identifier
            order by transaction_seq_num
        ) as prev_hash
    from all_bronze
),

new_versions as (
    select * from hashed
    where prev_hash is null
       or row_hash != prev_hash
),

final as (
    select
        policy_auto_vehicle_sk,
        policy_auto_sk,
        transaction_id,
        policy_number,
        policy_term_count,
        covered_item_number,
        covered_item_identifier,
        vehicle_change_type_code,
        busines_operation_group,
        vehicle_type,
        vehicle_make,
        vehicle_model,
        vehicle_model_year,
        primary_risk_state_code,
        policy_effective_date,
        policy_expiration_date,
        garaging_state,
        zip_code,
        transaction_seq_num,
        row_hash,
        case
            when lead(transaction_effective_date) over (
                partition by policy_number, policy_term_count, covered_item_identifier
                order by transaction_seq_num
            ) is null then true
            else false
        end                                                as is_current,
        lead(transaction_effective_date) over (
            partition by policy_number, policy_term_count, covered_item_identifier
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
