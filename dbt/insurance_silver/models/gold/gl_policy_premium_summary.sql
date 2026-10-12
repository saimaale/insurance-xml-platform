-- ---------------------------------------------------------------------------
-- gl_policy_premium_summary  (Gold)
-- Executive-level policy summary. One row per current policy version per term.
-- Aggregates vehicle count and coverage composition.
--
-- Grain  : (policy_number, policy_term_count)
-- Source : sl_policy, sl_vehicle, sl_vehicle_coverage
-- ---------------------------------------------------------------------------
with policy as (
    select
        policy_transaction_sk,
        policy_transaction_policy_sk,
        policy_auto_sk,
        policy_auto_jurisdiction_sk,
        policy_number,
        policy_term_count,
        transaction_id,
        transaction_seq_num,
        transaction_type_code,
        transaction_type_value,
        endorsement_type_code,
        agency_legal_name,
        agency_number,
        naic_code,
        policy_effective_date,
        policy_expiration_date,
        primary_risk_state_code,
        primary_risk_state_value,
        total_number_of_vehicles,
        total_number_of_drivers,
        private_passenger_vehicle_count,
        jurisdiction_state_code,
        garaging_state,
        city_name,
        zip_code,
        effective_from_dt,
        effective_to_dt,
        is_current
    from {{ ref('sl_policy') }}
    where is_current = true
),

-- Vehicle counts per current policy version via policy_auto_sk
vehicle_counts as (
    select
        v.policy_auto_sk,
        count(distinct v.covered_item_identifier)           as total_vehicles,
        count(distinct v.vehicle_type)                      as distinct_vehicle_types,
        count(distinct v.garaging_state)                    as garaging_states,
        array_join(
            array_agg(distinct v.vehicle_type), ', '
        )                                                   as vehicle_types
    from {{ ref('sl_vehicle') }} v
    where v.is_current = true
    group by v.policy_auto_sk
),

-- Coverage summary per policy via vehicle surrogate key chain
coverage_summary as (
    select
        v.policy_auto_sk,
        count(distinct c.coverage_group_code)               as distinct_coverages,
        sum(c.per_accident_limit_amount)                    as total_per_accident_limit,
        array_join(
            array_agg(distinct c.coverage_group_code), ', '
        )                                                   as coverage_groups,
        sum(case when c.coverage_change_type_code != 'Deleted' then 1 else 0 end) as active_coverages
    from {{ ref('sl_vehicle') }} v
    join {{ ref('sl_vehicle_coverage') }} c
        on c.policy_auto_vehicle_sk = v.policy_auto_vehicle_sk
    where c.is_current = true
    group by v.policy_auto_sk
),

final as (
    select
        -- ── Keys ──────────────────────────────────────────────────────────
        p.policy_number,
        p.policy_term_count,
        p.transaction_id,
        p.transaction_seq_num,
        p.policy_auto_sk,

        -- ── SCD2 version info ─────────────────────────────────────────────
        p.effective_from_dt,
        p.effective_to_dt,
        p.is_current,

        -- ── Transaction metadata ───────────────────────────────────────────
        p.transaction_type_code,
        p.transaction_type_value,
        p.endorsement_type_code,

        -- ── Policy details ────────────────────────────────────────────────
        p.agency_legal_name,
        p.agency_number,
        p.naic_code,
        p.policy_effective_date,
        p.policy_expiration_date,
        p.primary_risk_state_code,
        p.primary_risk_state_value,

        -- ── Location ──────────────────────────────────────────────────────
        p.jurisdiction_state_code,
        p.garaging_state,
        p.city_name,
        p.zip_code,

        -- ── Fleet composition ─────────────────────────────────────────────
        coalesce(p.total_number_of_vehicles, 0)             as declared_vehicles,
        coalesce(v.total_vehicles, 0)                       as active_vehicles,
        coalesce(p.total_number_of_drivers, 0)              as declared_drivers,
        v.distinct_vehicle_types,
        v.garaging_states,
        v.vehicle_types,

        -- ── Coverage summary ──────────────────────────────────────────────
        coalesce(c.distinct_coverages, 0)                   as distinct_coverages,
        coalesce(c.active_coverages, 0)                     as active_coverages,
        c.total_per_accident_limit,
        c.coverage_groups,

        -- ── Derived ───────────────────────────────────────────────────────
        case
            when coalesce(v.total_vehicles, 0) > 0
            then round(
                coalesce(c.total_per_accident_limit, 0) / v.total_vehicles, 2
            )
            else null
        end                                                 as avg_limit_per_vehicle

    from policy p
    left join vehicle_counts  v on v.policy_auto_sk = p.policy_auto_sk
    left join coverage_summary c on c.policy_auto_sk = p.policy_auto_sk
)

select * from final
