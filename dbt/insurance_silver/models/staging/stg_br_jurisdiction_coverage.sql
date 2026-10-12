-- ---------------------------------------------------------------------------
-- stg_br_jurisdiction_coverage
-- Jurisdiction-level ObjectCoverageInformation with attributes pivoted.
-- One row per (policy_auto_jurisdiction_sk, coverage_group_code).
--
-- Pivot map:
--   BureauCoverageType          → bureau_coverage_type          (text)
--   CoverageAffordedCode        → coverage_afforded_code        (text)
--   PerAccidentLimitAmount      → per_accident_limit_amount     (number)
--   PerAccidentLimitBasis       → per_accident_limit_basis      (text)
--   PerAccidentLimitType        → per_accident_limit_type       (text)
--   EmpNonOwnNumberOfEmployees  → emp_non_own_number_of_employees (number)
-- ---------------------------------------------------------------------------
select
    oci.object_coverage_information_sk,
    oci.parent_sk                                   as policy_auto_jurisdiction_sk,
    oci.transaction_id,
    oci.policy_number,
    oci.coverage_group_code,
    oci.coverage_type,
    oci.coverage_change_type_code,
    oci.coverage_effective_date,
    oci.coverage_expiration_date,

    -- ── Pivoted attribute columns ─────────────────────────────────────────
    max(case when oca.coverage_attribute_tag_name = 'BureauCoverageType'
        then oca.coverage_attribute_value_text end)         as bureau_coverage_type,

    max(case when oca.coverage_attribute_tag_name = 'CoverageAffordedCode'
        then oca.coverage_attribute_value_text end)         as coverage_afforded_code,

    max(case when oca.coverage_attribute_tag_name = 'PerAccidentLimitAmount'
        then oca.coverage_attribute_value_number end)       as per_accident_limit_amount,

    max(case when oca.coverage_attribute_tag_name = 'PerAccidentLimitBasis'
        then oca.coverage_attribute_value_text end)         as per_accident_limit_basis,

    max(case when oca.coverage_attribute_tag_name = 'PerAccidentLimitType'
        then oca.coverage_attribute_value_text end)         as per_accident_limit_type,

    max(case when oca.coverage_attribute_tag_name = 'EmpNonOwnNumberOfEmployees'
        then oca.coverage_attribute_value_number end)       as emp_non_own_number_of_employees,

    -- ── Audit ─────────────────────────────────────────────────────────────
    oci.source_file_name,
    cast(oci.source_load_ts as timestamp)                   as source_load_ts

from {{ source('bronze', 'br_object_coverage_information') }} oci
left join {{ source('bronze', 'br_object_coverage_attribute') }} oca
    on oca.object_coverage_information_sk = oci.object_coverage_information_sk
where oci.parent_type = 'jurisdiction'
group by
    oci.object_coverage_information_sk,
    oci.parent_sk,
    oci.transaction_id,
    oci.policy_number,
    oci.coverage_group_code,
    oci.coverage_type,
    oci.coverage_change_type_code,
    oci.coverage_effective_date,
    oci.coverage_expiration_date,
    oci.source_file_name,
    oci.source_load_ts
