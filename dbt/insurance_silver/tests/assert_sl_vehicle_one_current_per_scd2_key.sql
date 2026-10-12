-- ---------------------------------------------------------------------------
-- Test: assert_sl_vehicle_one_current_per_scd2_key
--
-- SCD2 invariant: at most ONE is_current=true row per
-- (policy_number, policy_term_count, covered_item_identifier).
--
-- Returns rows when violated (0 rows = PASS).
-- ---------------------------------------------------------------------------
select
    policy_number,
    policy_term_count,
    covered_item_identifier,
    count(*) as current_row_count
from {{ ref('sl_vehicle') }}
where is_current = true
group by policy_number, policy_term_count, covered_item_identifier
having count(*) > 1
