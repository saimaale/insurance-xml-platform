-- ---------------------------------------------------------------------------
-- Test: assert_sl_policy_expired_has_nonnull_effective_to
--
-- SCD2 invariant: a row with is_current=false must have effective_to_dt IS NOT NULL.
-- An expired row with no end date means the record was closed without being
-- properly dated — indicates a MERGE or expiry logic failure.
--
-- Returns rows when violated (0 rows = PASS).
-- ---------------------------------------------------------------------------
select
    policy_number,
    policy_term_count,
    transaction_seq_num,
    effective_from_dt,
    effective_to_dt
from {{ ref('sl_policy') }}
where is_current = false
  and effective_to_dt is null
