-- ---------------------------------------------------------------------------
-- Test: assert_sl_policy_current_has_null_effective_to
--
-- SCD2 invariant: a row with is_current=true must have effective_to_dt IS NULL.
-- If a current row has an end date, the MERGE logic has a bug.
--
-- Returns rows when violated (0 rows = PASS).
-- ---------------------------------------------------------------------------
select
    policy_number,
    policy_term_count,
    transaction_seq_num,
    effective_to_dt
from {{ ref('sl_policy') }}
where is_current = true
  and effective_to_dt is not null
