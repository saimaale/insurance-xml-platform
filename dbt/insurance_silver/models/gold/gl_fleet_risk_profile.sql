-- ---------------------------------------------------------------------------
-- gl_fleet_risk_profile  (Gold)
-- Vehicle-level risk profile for underwriting analysis.
-- One row per current vehicle version with coverage summary.
--
-- Grain  : (policy_number, policy_term_count, covered_item_identifier)
-- Source : sl_vehicle, sl_vehicle_coverage
-- ---------------------------------------------------------------------------
with vehicles as (
    select
        policy_auto_vehicle_sk,
        policy_auto_sk,
        transaction_id,
        policy_number,
        policy_term_count,
        covered_item_identifier,
        covered_item_number,
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
        effective_from_dt,
        effective_to_dt,
        is_current
    from {{ ref('sl_vehicle') }}
    where is_current = true
),

-- Coverage summary per current vehicle — joined on Bronze surrogate key
coverage_summary as (
    select
        c.policy_auto_vehicle_sk,
        count(distinct c.coverage_group_code)               as coverage_count,
        array_join(
            array_agg(distinct c.coverage_group_code), ', '
        )                                                   as coverage_groups,
        -- Aggregate limits across all active coverages
        sum(c.per_accident_limit_amount)                    as total_per_accident_limit,
        max(c.deductible_amount)                            as max_deductible_amount,
        -- Count active vs deleted coverages
        sum(case when c.coverage_change_type_code != 'Deleted' then 1 else 0 end) as active_coverage_count,
        sum(case when c.coverage_change_type_code  = 'Deleted' then 1 else 0 end) as deleted_coverage_count
    from {{ ref('sl_vehicle_coverage') }} c
    where c.is_current = true
    group by c.policy_auto_vehicle_sk
),

final as (
    select
        -- ── Keys ──────────────────────────────────────────────────────────
        v.policy_auto_vehicle_sk,
        v.policy_auto_sk,
        v.transaction_id,
        v.policy_number,
        v.policy_term_count,
        v.covered_item_identifier,
        v.covered_item_number,
        v.transaction_seq_num,

        -- ── SCD2 version info ─────────────────────────────────────────────
        v.effective_from_dt,
        v.effective_to_dt,
        v.is_current,

        -- ── Policy context ────────────────────────────────────────────────
        v.primary_risk_state_code,
        v.policy_effective_date,
        v.policy_expiration_date,

        -- ── Vehicle identity ──────────────────────────────────────────────
        v.vehicle_make,
        v.vehicle_model,
        v.vehicle_model_year,
        v.vehicle_type,
        v.busines_operation_group,
        v.vehicle_change_type_code,

        -- ── Location ──────────────────────────────────────────────────────
        v.garaging_state,
        v.zip_code,

        -- ── Coverage summary ──────────────────────────────────────────────
        coalesce(c.coverage_count, 0)                       as coverage_count,
        coalesce(c.active_coverage_count, 0)                as active_coverage_count,
        coalesce(c.deleted_coverage_count, 0)               as deleted_coverage_count,
        c.total_per_accident_limit,
        c.max_deductible_amount,
        c.coverage_groups

    from vehicles v
    left join coverage_summary c
        on c.policy_auto_vehicle_sk = v.policy_auto_vehicle_sk
)

select * from final
