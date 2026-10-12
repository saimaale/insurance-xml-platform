# Insurance XML Platform

A cloud-native data platform demonstrating end-to-end analytics engineering across the full Medallion Architecture — from raw XML policy ingestion through to Gold-layer reporting.

**Stack:** AWS Glue · S3 · Athena · Apache Iceberg · dbt · Terraform · Python

---

## Architecture

```
XML Policy Files (S3)
        │
        ▼
┌─────────────────┐
│   Bronze Layer  │  AWS Glue ETL job shreds hierarchical XML into
│  (Apache Iceberg│  normalized Parquet/Iceberg tables:
│   via Athena)   │  policy · vehicle · vehicle_coverage · jurisdiction_coverage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Silver Layer  │  dbt incremental models implement SCD Type 2:
│  (dbt + Iceberg)│  sl_policy · sl_vehicle · sl_vehicle_coverage · sl_jurisdiction_coverage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Gold Layer    │  dbt models aggregate Silver current-state (is_current=true):
│  (dbt + Athena) │  gl_policy_premium_summary · gl_fleet_risk_profile
└─────────────────┘
```

---

## Project Structure

```
insurance-xml-platform/
├── ingestion/
│   ├── sample_xml/             # 36 policy XML files (10 policies × 3-4 transactions each)
│   └── glue_jobs/
│       └── shred_policy_xml_to_bronze.py   # AWS Glue ETL job
├── dbt/
│   └── insurance_silver/
│       ├── models/
│       │   ├── silver/         # sl_policy, sl_vehicle, sl_vehicle_coverage, sl_jurisdiction_coverage
│       │   └── gold/           # gl_policy_premium_summary, gl_fleet_risk_profile
│       ├── tests/              # Custom SCD2 invariant tests
│       ├── dbt_project.yml
│       └── profiles.yml        # Athena connection config (demo only — use ~/.dbt/ in production)
├── infra/
│   └── terraform/              # S3 buckets, Glue database, Athena workgroup, IAM roles
├── docs/
│   └── bronze_policy_xml_shredder/   # Bronze layer source code and documentation
├── cli_commands_reference.md   # Full AWS CLI + dbt run command reference
└── README.md
```

---

## Key Design Decisions

### SCD Type 2 in dbt with Apache Iceberg
Silver models use dbt's `incremental` materialization with Iceberg's `MERGE` strategy. Each model tracks full policy history using composite natural keys instead of surrogate keys:

- `sl_policy` — keyed on `(policy_number, policy_term_count, transaction_seq_num)`
- `sl_vehicle` — adds `covered_item_identifier`
- `sl_vehicle_coverage` — adds `coverage_group_code`
- `sl_jurisdiction_coverage` — keyed on `(policy_number, policy_term_count, coverage_group_code)`

### Three-Path Incremental Loading
All Silver models support three load modes controlled via a single dbt variable — no code changes required:

| Mode | Command | Use Case |
|------|---------|----------|
| Historical | `dbt run --full-refresh` | First load or full rebuild |
| Incremental | `dbt run` | Daily/ongoing loads |
| Reprocess | `dbt run --vars '{"load_type":"reprocess","start_date":"...","end_date":"..."}'` | Backfill a date range |

### Coverage Lifecycle as First-Class SCD2 Signal
`coverage_change_type_code` (Added / Changed / Deleted / NoChange) is included in each coverage row's `row_hash`. This means any coverage deletion event automatically changes the hash and triggers correct SCD2 version expiry — without needing a separate deletion pipeline.

### Two Coverage Tables vs One
Vehicle coverages (`sl_vehicle_coverage`) and jurisdiction-level coverages (`sl_jurisdiction_coverage`) are modeled as separate Silver tables because they operate at different grains and have different parent keys. Combining them would require nullable join keys and complicate SCD2 logic.

---

## XML Test Scenarios

The `ingestion/sample_xml/` directory includes 36 XML files covering the full policy lifecycle:

| Scenario | Files | SCD2 Event |
|----------|-------|------------|
| New Business | `*_txn1_newbusiness.xml` | Initial insert |
| Endorsement | `*_txn2_endorsement.xml` | Policy/coverage change |
| Renewal | `*_txn3_renewal.xml` | New policy term |
| Cancellation | `P10000003/5/8_txn3_cancellation.xml` | Policy termination |
| Vehicle Delete | `P10000001_txn4_endorsement.xml` | `VehicleChangeTypeCode=Deleted` |
| Coverage Delete | `P10000002_txn4_endorsement.xml` | `CoverageChangeTypeCode=Deleted` |
| Coverage Add | `P10000004_txn4_endorsement.xml` | `CoverageChangeTypeCode=Added` |
| Vehicle Add | `P10000006_txn4_endorsement.xml` | `VehicleChangeTypeCode=Added` |
| Limit Change | `P10000009_txn4_endorsement.xml` | `CoverageChangeTypeCode=Changed` |

---

## dbt Tests

### Schema Tests (`models/silver/schema.yml`)
- `dbt_utils.unique_combination_of_columns` — enforces composite key uniqueness on all Silver models
- `not_null` — on all SCD2 key columns and `is_current`, `row_hash`, `effective_from_dt`
- `accepted_values` — `coverage_change_type_code` in `[Added, Changed, Deleted, NoChange]`

### Custom Singular Tests (`tests/`)
- `assert_sl_policy_one_current_per_scd2_key` — at most one `is_current=true` row per policy/term
- `assert_sl_policy_current_has_null_effective_to` — current rows must have `effective_to_dt IS NULL`
- `assert_sl_policy_expired_has_nonnull_effective_to` — expired rows must have a close date
- Equivalent tests for `sl_vehicle`, `sl_vehicle_coverage`, `sl_jurisdiction_coverage`

---

## Infrastructure (Terraform)

Provisions the full AWS environment:
- S3 buckets: raw XML landing, Bronze Parquet, Athena query results
- AWS Glue database and crawler
- Athena workgroup
- IAM roles and policies for Glue and Athena

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

---

## Running the Pipeline

See [`cli_commands_reference.md`](cli_commands_reference.md) for the full command reference. Quick start:

```bash
# 1. Upload XML files to S3
aws s3 cp ingestion/sample_xml/ s3://ins-xml-dev-raw/policy_xml/ --recursive

# 2. Run Glue ETL job (Bronze layer)
aws glue start-job-run --job-name shred-policy-xml-to-bronze

# 3. Run dbt Silver + Gold (historical load)
cd dbt/insurance_silver
dbt deps
dbt run --full-refresh

# 4. Run dbt tests
dbt test
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Ingestion | AWS Glue (ETL job), Python |
| Storage | Amazon S3, Apache Iceberg, Parquet |
| Query Engine | Amazon Athena |
| Transformation | dbt-athena, SQL, Jinja |
| Infrastructure | Terraform |
| Testing | dbt schema tests, custom singular tests |
