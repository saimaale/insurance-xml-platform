-- ---------------------------------------------------------------------------
-- sl_jurisdiction_coverage  (Silver — Incremental SCD Type 2)
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
-- Grain        : (policy_number, policy_term_count, coverage_group_code,
--                transaction_seq_num)
-- SCD2 key     : (policy_number, policy_term_count, coverage_group_code)
-- Current rows : is_current = true
-- Active rows  : is_current = true AND coverage_change_type_code != 'Deleted'
-- ---------------------------------------------------------------------------
{{ config(
    materialized          = 'incremental',
    incremental_strategy  = 'merge',
    unique_key            = ['policy_number', 'policy_term_count',
                             'coverage_group_code', 'transaction_seq_num'],
    table_type            = 'iceberg',
    on_schema_change      = 'sync_all_columns',
    s3_data_dir           = 's3://ins-xml-dev-silver/dbt/sl_jurisdiction_coverage/'
) }}

{% set load_type = var('load_type', 'transactional') %}

-- ── Step 1: Coverage Bronze joined to policy Silver for context ──────────────
with all_bronze as (
    select
        c.object_coverage_information_sk,
        c.policy_auto_jurisdiction_sk,
        c.transaction_id,
        c.policy_number,
        c.coverage_group_code,
        c.coverage_type,
        c.coverage_change_type_code,
        c.coverage_effective_date,
        c.coverage_expiration_date,
        c.bureau_coverage_type,
        c.coverage_afforded_code,
        c.per_accident_limit_amount,
        c.per_accident_limit_basis,
        c.per_accident_limit_type,
        c.emp_non_own_number_of_employees,
        -- policy context from sl_policy (all versions matched on Bronze SK)
        p.policy_term_count,
        p.transaction_seq_num,
        p.primary_risk_state_code,
        p.jurisdiction_state_code,
        p.garaging_state,
        p.zip_code,
        p.policy_effective_date,
        p.policy_expiration_date,
        p.transaction_effective_date,
        c.source_file_name,
        c.source_load_ts,
        -- SCD2 hash: coverage status + business attributes
        to_hex(md5(to_utf8(concat(
            coalesce(c.coverage_change_type_code,                        ''),
            coalesce(cast(c.per_accident_limit_amount as varchar),       ''),
            coalesce(cast(c.emp_non_own_number_of_employees as varchar), ''),
            coalesce(c.coverage_afforded_code,                          ''),
            coalesce(c.bureau_coverage_type,                             ''),
            coalesce(c.per_accident_limit_basis,                         ''),
            coalesce(c.per_accident_limit_type,                          '')
        )))) as row_hash
    from {{ ref('stg_br_jurisdiction_coverage') }} c
    join {{ ref('sl_policy') }} p
        on p.policy_auto_jurisdiction_sk = c.policy_auto_jurisdiction_sk
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
        coverage_group_code,
        max(transaction_seq_num) as max_seq
    from {{ this }}
    group by policy_number, policy_term_count, coverage_group_code
),

new_transactions as (
    select b.*
    from all_bronze b
    left join watermark w
        on  w.policy_number       = b.policy_number
        and w.policy_term_count   = b.policy_term_count
        and w.coverage_group_code = b.coverage_group_code
    where w.max_seq is null
       or b.transaction_seq_num > w.max_seq
),

{% endif %}

records_to_expire as (
    select
        s.object_coverage_information_sk,
        s.policy_auto_jurisdiction_sk,
        s.transaction_id,
        s.policy_number,
        s.policy_term_count,
        s.coverage_group_code,
        s.coverage_type,
        s.coverage_change_type_code,
        s.coverage_effective_date,
        s.coverage_expiration_date,
        s.bureau_coverage_type,
        s.coverage_afforded_code,
        s.per_accident_limit_amount,
        s.per_accident_limit_basis,
        s.per_accident_limit_type,
        s.emp_non_own_number_of_employees,
        s.primary_risk_state_code,
        s.jurisdiction_state_code,
        s.garaging_state,
        s.zip_code,
        s.policy_effective_date,
        s.policy_expiration_date,
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
        on  n.policy_number       = s.policy_number
        and n.policy_term_count   = s.policy_term_count
        and n.coverage_group_code = s.coverage_group_code
    where s.is_current = true
      and s.row_hash  != n.row_hash
),

new_records as (
    select
        object_coverage_information_sk,
        policy_auto_jurisdiction_sk,
        transaction_id,
        policy_number,
        policy_term_count,
        coverage_group_code,
        coverage_type,
        coverage_change_type_code,
        coverage_effective_date,
        coverage_expiration_date,
        bureau_coverage_type,
        coverage_afforded_code,
        per_accident_limit_amount,
        per_accident_limit_basis,
        per_accident_limit_type,
        emp_non_own_number_of_employees,
        primary_risk_state_code,
        jurisdiction_state_code,
        garaging_state,
        zip_code,
        policy_effective_date,
        policy_expiration_date,
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
            partition by policy_number, policy_term_count, coverage_group_code
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
        object_coverage_information_sk,
        policy_auto_jurisdiction_sk,
        transaction_id,
        policy_number,
        policy_term_count,
        coverage_group_code,
        coverage_type,
        coverage_change_type_code,
        coverage_effective_date,
        coverage_expiration_date,
        bureau_coverage_type,
        coverage_afforded_code,
        per_accident_limit_amount,
        per_accident_limit_basis,
        per_accident_limit_type,
        emp_non_own_number_of_employees,
        primary_risk_state_code,
        jurisdiction_state_code,
        garaging_state,
        zip_code,
        policy_effective_date,
        policy_expiration_date,
        transaction_seq_num,
        row_hash,
        case
            when lead(transaction_effective_date) over (
                partition by policy_number, policy_term_count, coverage_group_code
                order by transaction_seq_num
            ) is null then true
            else false
        end                                                as is_current,
        lead(transaction_effective_date) over (
            partition by policy_number, policy_term_count, coverage_group_code
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
