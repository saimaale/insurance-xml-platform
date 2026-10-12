-- ---------------------------------------------------------------------------
-- Test: assert_sl_vehicle_coverage_current_has_null_effective_to
--
-- SCD2 invariant: a row with is_current=true must have effective_to_dt IS NULL.
--
-- Returns rows when violated (0 rows = PASS).
-- ---------------------------------------------------------------------------
select
    policy_number,
    policy_term_count,
    covered_item_identifier,
    coverage_group_code,
    transaction_seq_num,
    effective_to_dt
from {{ ref('sl_vehicle_coverage') }}
where is_current = true
  and effective_to_dt is not null
