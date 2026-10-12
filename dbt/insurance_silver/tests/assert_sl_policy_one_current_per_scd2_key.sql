-- ---------------------------------------------------------------------------
-- Test: assert_sl_policy_one_current_per_scd2_key
--
-- SCD2 invariant: there must be at most ONE is_current=true row per
-- (policy_number, policy_term_count) combination.
--
-- Returns rows when violated (0 rows = PASS).
-- ---------------------------------------------------------------------------
select
    policy_number,
    policy_term_count,
    count(*) as current_row_count
from {{ ref('sl_policy') }}
where is_current = true
group by policy_number, policy_term_count
having count(*) > 1
