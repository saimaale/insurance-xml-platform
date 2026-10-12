-- ---------------------------------------------------------------------------
-- Test: assert_sl_jurisdiction_coverage_one_current_per_scd2_key
--
-- SCD2 invariant: at most ONE is_current=true row per
-- (policy_number, policy_term_count, coverage_group_code).
--
-- Returns rows when violated (0 rows = PASS).
-- ---------------------------------------------------------------------------
select
    policy_number,
    policy_term_count,
    coverage_group_code,
    count(*) as current_row_count
from {{ ref('sl_jurisdiction_coverage') }}
where is_current = true
group by policy_number, policy_term_count, coverage_group_code
having count(*) > 1
