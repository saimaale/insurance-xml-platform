# Insurance XML Platform — CLI Commands Reference

All command-line queries used throughout the project, organised by phase.

---

## 1. XML Validation

```bash
# Validate an XML file with xmllint
xmllint --noout policy_real_ex.xml

# Validate all generated XML files at once
for f in /Users/maalesaisantoshreddy/insurance-xml-platform/ingestion/sample_xml/*.xml; do
  xmllint --noout "$f" && echo "OK: $f" || echo "FAIL: $f"
done
```

---

## 2. Generate Sample XML Files

```bash
# Run the XML generator script
python3 /sessions/quirky-gifted-planck/generate_xmls.py
```

---

## 3. AWS S3 — Landing Bucket (XML Files)

```bash
# List all S3 buckets
aws s3 ls

# List XML files in the landing bucket
aws s3 ls s3://ins-xml-dev-landing/xml/

# List all XML files recursively and count
aws s3 ls s3://ins-xml-dev-landing/xml/ --recursive | grep "\.xml" | wc -l

# Delete all old XML files (keep DataSync metadata)
aws s3 rm s3://ins-xml-dev-landing/xml/ \
  --exclude ".aws-datasync/*" \
  --include "*.xml" \
  --recursive

# Sync local XML folder to S3 (upload new + delete removed files)
aws s3 sync /Users/maalesaisantoshreddy/insurance-xml-platform/ingestion/sample_xml/ \
  s3://ins-xml-dev-landing/xml/ \
  --exclude "policy_real_ex.xml" \
  --delete

# Upload new generated XML files to S3
aws s3 cp /Users/maalesaisantoshreddy/insurance-xml-platform/ingestion/sample_xml/ \
  s3://ins-xml-dev-landing/xml/ \
  --recursive \
  --include "*.xml"

# Inspect a specific XML file from S3
aws s3 cp s3://ins-xml-dev-landing/xml/P10000001_txn1_newbusiness.xml - | head -60
```

---

## 4. AWS S3 — Wipe Layer Data

```bash
# Wipe all Bronze Iceberg data
aws s3 rm s3://ins-xml-dev-bronze/ --recursive

# Wipe all Silver data
aws s3 rm s3://ins-xml-dev-silver/dbt/ --recursive

# Wipe Gold data only
aws s3 rm s3://ins-xml-dev-silver/gold/ --recursive

# Wipe everything in Silver bucket (Silver + Gold)
aws s3 rm s3://ins-xml-dev-silver/ --recursive
```

---

## 5. AWS Glue — Catalog (Databases & Tables)

```bash
# Get the location URI of the Silver database
aws glue get-database --name insurance_silver \
  --query 'Database.LocationUri' \
  --output text

# List all tables in the Bronze database
aws glue get-tables --database-name insurance_bronze \
  --query 'TableList[*].Name' \
  --output text

# Drop a single Glue catalog table
aws glue delete-table --database-name insurance_bronze --name br_policy_transaction

# Drop all Bronze tables in a loop
for table in br_policy_transaction br_policy_transaction_policy br_policy_auto \
             br_policy_auto_jurisdiction br_policy_auto_location br_policy_auto_vehicle \
             br_object_coverage_information br_object_coverage_attribute; do
  aws glue delete-table --database-name insurance_bronze --name $table 2>/dev/null && \
    echo "Dropped $table" || echo "Not found: $table"
done

# Drop all Silver tables in a loop
for table in sl_policy sl_vehicle sl_vehicle_coverage sl_jurisdiction_coverage; do
  aws glue delete-table --database-name insurance_silver --name $table 2>/dev/null && \
    echo "Dropped $table" || echo "Not found: $table"
done

# Drop all Gold tables in a loop
for table in gl_fleet_risk_profile gl_policy_premium_summary; do
  aws glue delete-table --database-name insurance_gold --name $table 2>/dev/null && \
    echo "Dropped $table" || echo "Not found: $table"
done
```

---

## 6. AWS Glue — Jobs

```bash
# List all Glue jobs
aws glue list-jobs --output text

# Get the default arguments (config) for a job
aws glue get-job --job-name ins-xml-dev-xml-shredder \
  --query 'Job.DefaultArguments' \
  --output json

# Trigger the Glue XML shredder job
aws glue start-job-run --job-name ins-xml-dev-xml-shredder

# Get the latest job run ID
aws glue get-job-runs --job-name ins-xml-dev-xml-shredder \
  --query 'JobRuns[0].Id' \
  --output text

# Check the status of the latest job run
aws glue get-job-run \
  --job-name ins-xml-dev-xml-shredder \
  --run-id $(aws glue get-job-runs --job-name ins-xml-dev-xml-shredder \
             --query 'JobRuns[0].Id' --output text) \
  --query 'JobRun.JobRunState' \
  --output text
```

---

## 7. AWS CloudWatch — Glue Job Logs

```bash
# List all Glue-related log groups
aws logs describe-log-groups \
  --log-group-name-prefix "/aws-glue" \
  --query 'logGroups[*].logGroupName' \
  --output text

# Find log streams for the shredder job
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --log-stream-name-prefix "ins-xml-dev-xml-shredder" \
  --query 'logStreams[*].logStreamName' \
  --output text

# Pull error logs for a specific job run
JOB_RUN_ID=$(aws glue get-job-runs \
  --job-name ins-xml-dev-xml-shredder \
  --query 'JobRuns[0].Id' \
  --output text)

aws logs get-log-events \
  --log-group-name /aws-glue/jobs/error \
  --log-stream-name "ins-xml-dev-xml-shredder/$JOB_RUN_ID" \
  --limit 200 \
  --query 'events[*].message' \
  --output text 2>&1 | tail -150

# Pull output logs for a specific job run
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/output \
  --log-stream-name "ins-xml-dev-xml-shredder/$JOB_RUN_ID" \
  --limit 200 \
  --query 'events[*].message' \
  --output text 2>&1 | tail -150
```

---

## 8. Upload Glue Script to S3

```bash
# Upload the updated Glue shredder script
aws s3 cp \
  /Users/maalesaisantoshreddy/insurance-xml-platform/ingestion/glue_jobs/shred_policy_xml_to_bronze.py \
  s3://ins-xml-dev-landing/scripts/shred_policy_xml_to_bronze.py
```

---

## 9. dbt

```bash
# Navigate to the dbt project
cd /Users/maalesaisantoshreddy/insurance-xml-platform/dbt/insurance_silver

# ── Silver: Historical load (full rebuild from all Bronze transactions) ──
# Use after initial setup or whenever Bronze data is corrected/reloaded.
# --full-refresh forces is_incremental() = false, triggering the LAG/LEAD path.
dbt run --select silver --full-refresh --profiles-dir .

# ── Silver: Transactional load (incremental — new transactions only) ──
# Default daily run. Watermark finds the last processed seq_num per policy/term.
dbt run --select silver --profiles-dir .

# ── Silver: Reprocess (date-range backfill) ──
# Use when Bronze source data was corrected for a known historical period.
# Re-merges all transactions whose effective date falls within the window.
# --vars is required here; start_date and end_date must be provided.
dbt run --select silver \
        --vars '{"load_type": "reprocess", "start_date": "2024-01-01", "end_date": "2024-06-30"}' \
        --profiles-dir .

# ── Gold: Run Gold models ──
dbt run --select gold --profiles-dir .

# ── Run specific model only ──
dbt run --select sl_policy --profiles-dir .
dbt run --select sl_vehicle_coverage --full-refresh --profiles-dir .

# ── Run all models ──
dbt run --profiles-dir .

# Run dbt tests
dbt test --profiles-dir .

# Show model lineage / compile without running
dbt compile --profiles-dir .

# Show dbt debug info (connection check)
dbt debug --profiles-dir .
```

### Silver Load Type Behaviour

| Command | `is_incremental()` | `load_type` var | Path | When to use |
|---|---|---|---|---|
| `--full-refresh` | `false` | n/a | Historical — LAG/LEAD window functions across all Bronze | Initial load, Bronze data corrections, XML fixes |
| Normal run | `true` | `transactional` (default) | Transactional — watermark finds new seq_nums, expire + insert | Daily processing of new transactions |
| Normal run + `--vars` | `true` | `reprocess` | Reprocess — date range filter, expire + insert for matched window | Backfill when historical Bronze records are corrected |

---

## 10. Full Reload Sequence (End to End)

Use this when XML data is corrected and everything needs to be reloaded from scratch.

```bash
# ── Step 1: Fix and re-upload XMLs ──
aws s3 sync /Users/maalesaisantoshreddy/insurance-xml-platform/ingestion/sample_xml/ \
    s3://ins-xml-dev-landing/xml/ \
    --exclude "policy_real_ex.xml" \
    --delete

# ── Step 2: Drop Bronze tables ──
for table in br_policy_transaction br_policy_transaction_policy br_policy_auto \
             br_policy_auto_vehicle br_policy_auto_jurisdiction br_policy_auto_location \
             br_object_coverage_information br_object_coverage_attribute; do
  aws glue delete-table --database-name insurance_bronze --name $table 2>/dev/null \
    && echo "Dropped $table" || echo "Not found: $table"
done

# ── Step 3: Wipe Bronze S3 and rerun Glue ──
aws s3 rm s3://ins-xml-dev-bronze/ --recursive
aws glue start-job-run --job-name <your-glue-job-name>

# Check Glue job status
aws glue get-job-runs --job-name <your-glue-job-name> \
    --query 'JobRuns[0].{State:JobRunState,Started:StartedOn,Completed:CompletedOn}' \
    --output table

# ── Step 4: Drop Silver tables ──
for table in sl_policy sl_vehicle sl_vehicle_coverage sl_jurisdiction_coverage; do
  aws glue delete-table --database-name insurance_silver --name $table 2>/dev/null \
    && echo "Dropped $table" || echo "Not found: $table"
done
aws s3 rm s3://ins-xml-dev-silver/dbt/ --recursive

# ── Step 5: Run Silver historical load ──
cd /Users/maalesaisantoshreddy/insurance-xml-platform/dbt/insurance_silver
dbt run --select silver --full-refresh --profiles-dir .

# ── Step 6: Drop Gold tables ──
for table in gl_fleet_risk_profile gl_policy_premium_summary; do
  aws glue delete-table --database-name insurance_gold --name $table 2>/dev/null \
    && echo "Dropped $table" || echo "Not found: $table"
done
aws s3 rm s3://ins-xml-dev-silver/gold/ --recursive

# ── Step 7: Run Gold ──
dbt run --select gold --profiles-dir .
```

---

## 11. Athena — Bronze Row Count Check

```sql
SELECT 'br_policy_transaction'           AS tbl, COUNT(*) AS cnt FROM insurance_bronze.br_policy_transaction
UNION ALL
SELECT 'br_policy_transaction_policy',           COUNT(*) FROM insurance_bronze.br_policy_transaction_policy
UNION ALL
SELECT 'br_policy_auto',                         COUNT(*) FROM insurance_bronze.br_policy_auto
UNION ALL
SELECT 'br_policy_auto_jurisdiction',            COUNT(*) FROM insurance_bronze.br_policy_auto_jurisdiction
UNION ALL
SELECT 'br_policy_auto_location',               COUNT(*) FROM insurance_bronze.br_policy_auto_location
UNION ALL
SELECT 'br_policy_auto_vehicle',                COUNT(*) FROM insurance_bronze.br_policy_auto_vehicle
UNION ALL
SELECT 'br_object_coverage_information',        COUNT(*) FROM insurance_bronze.br_object_coverage_information
UNION ALL
SELECT 'br_object_coverage_attribute',          COUNT(*) FROM insurance_bronze.br_object_coverage_attribute
ORDER BY tbl;
```

---

## 12. Athena — Coverage Attribute Query (Surrogate Key Joins)

```sql
WITH latest_txn AS (
    SELECT
        ptp.policy_number,
        ptp.policy_transaction_policy_sk,
        ptp.policy_transaction_sk,
        ROW_NUMBER() OVER (
            PARTITION BY ptp.policy_number
            ORDER BY pt.source_load_ts DESC
        ) AS rn
    FROM insurance_bronze.br_policy_transaction_policy ptp
    JOIN insurance_bronze.br_policy_transaction pt
        ON ptp.policy_transaction_sk = pt.policy_transaction_sk
)

SELECT
    lt.policy_number,
    oca.covered_item_identifier,
    oca.coverage_group_code,
    oca.coverage_attribute_tag_name,
    oca.coverage_attribute_type,
    oca.coverage_attribute_value_text,
    oca.coverage_attribute_value_number,
    oca.coverage_attribute_change_type_code
FROM latest_txn lt
JOIN insurance_bronze.br_policy_auto pa
    ON pa.policy_transaction_policy_sk = lt.policy_transaction_policy_sk
JOIN insurance_bronze.br_policy_auto_vehicle pav
    ON pav.policy_auto_sk = pa.policy_auto_sk
JOIN insurance_bronze.br_object_coverage_information oci
    ON oci.parent_sk = pav.policy_auto_vehicle_sk
JOIN insurance_bronze.br_object_coverage_attribute oca
    ON oca.object_coverage_information_sk = oci.object_coverage_information_sk
WHERE lt.rn = 1
  AND lt.policy_number = 'P10000001'
ORDER BY
    pav.covered_item_identifier,
    oci.coverage_group_code,
    oca.coverage_attribute_tag_name;
```

---

## 13. Athena — Silver Validation Queries

```sql
-- SCD2 versions per policy and term
SELECT
    policy_number,
    policy_term_count,
    count(*)                   AS version_count,
    min(transaction_seq_num)   AS first_seq,
    max(transaction_seq_num)   AS latest_seq,
    sum(case when is_current then 1 else 0 end) AS active_versions
FROM insurance_silver.sl_policy
GROUP BY 1, 2
ORDER BY 1, 2;

-- Verify renewal policies have 2 active terms simultaneously
SELECT
    policy_number,
    policy_term_count,
    transaction_seq_num,
    is_current,
    effective_from_dt,
    effective_to_dt,
    transaction_type_code
FROM insurance_silver.sl_policy
WHERE policy_number = 'P10000001'
ORDER BY policy_term_count, transaction_seq_num;

-- Get current active coverages for a policy
SELECT
    vc.policy_number,
    vc.policy_term_count,
    vc.covered_item_identifier,
    vc.coverage_group_code,
    vc.coverage_change_type_code,
    vc.per_accident_limit_amount,
    vc.deductible_amount,
    vc.coverage_afforded_code,
    vc.effective_from_dt
FROM insurance_silver.sl_vehicle_coverage vc
WHERE vc.policy_number = 'P10000001'
  AND vc.is_current = true
  AND vc.coverage_change_type_code != 'Deleted'
ORDER BY vc.covered_item_identifier, vc.coverage_group_code;

-- Row count comparison Bronze vs Silver
SELECT 'bronze_transactions' AS layer, count(*) FROM insurance_bronze.br_policy_transaction
UNION ALL
SELECT 'silver_policy',       count(*) FROM insurance_silver.sl_policy
UNION ALL
SELECT 'silver_vehicle',      count(*) FROM insurance_silver.sl_vehicle
UNION ALL
SELECT 'silver_veh_coverage', count(*) FROM insurance_silver.sl_vehicle_coverage
UNION ALL
SELECT 'silver_jur_coverage', count(*) FROM insurance_silver.sl_jurisdiction_coverage;
```

---

## 14. Athena — Gold Validation Queries

```sql
-- Fleet risk profile for a policy
SELECT *
FROM insurance_gold.gl_fleet_risk_profile
WHERE policy_number = 'P10000001'
ORDER BY policy_term_count, covered_item_identifier;

-- Policy premium summary across all policies
SELECT
    policy_number,
    policy_term_count,
    transaction_type_code,
    declared_vehicles,
    active_vehicles,
    distinct_coverages,
    active_coverages,
    total_per_accident_limit,
    avg_limit_per_vehicle
FROM insurance_gold.gl_policy_premium_summary
ORDER BY policy_number, policy_term_count;
```

---

## 15. Terraform — Infrastructure Provisioning

All infrastructure (S3 buckets, Glue jobs, Athena workgroup, IAM roles, DataSync) is
defined in `infra/terraform/` with modules for each service.

```bash
# Navigate to the Terraform directory
cd /Users/maalesaisantoshreddy/insurance-xml-platform/infra/terraform

# Initialise Terraform (download providers & modules)
terraform init

# Preview what will be created / changed
terraform plan

# Apply and provision all infrastructure
terraform apply

# Apply without interactive confirmation prompt
terraform apply -auto-approve

# Provision only a specific module (e.g. S3 buckets)
terraform apply -target=module.s3

# Provision only a specific module (e.g. Glue job)
terraform apply -target=module.glue

# Provision only a specific module (e.g. Athena workgroup)
terraform apply -target=module.athena

# Provision only a specific module (e.g. IAM roles)
terraform apply -target=module.iam

# Provision only a specific module (e.g. DataSync)
terraform apply -target=module.datasync

# Show current Terraform state (what is provisioned)
terraform show

# List all resources tracked in state
terraform state list

# Inspect a specific resource in state
terraform state show module.glue.aws_glue_job.xml_shredder

# Destroy all infrastructure (use with caution)
terraform destroy

# Destroy only a specific module
terraform destroy -target=module.s3

# Validate Terraform config syntax without applying
terraform validate

# Format all .tf files to canonical style
terraform fmt -recursive

# Output values (e.g. bucket names, job ARNs)
terraform output
```

### Modules Provisioned

| Module | Resources Created |
|---|---|
| `module.s3` | `ins-xml-dev-landing`, `ins-xml-dev-bronze` S3 buckets |
| `module.glue` | `ins-xml-dev-xml-shredder` Glue job, `insurance_bronze` Glue database |
| `module.athena` | Athena workgroup, `insurance_silver` Glue database |
| `module.iam` | Glue execution role, S3 access policies |
| `module.datasync` | DataSync task: local → `ins-xml-dev-landing/xml/` |

---

## Project Architecture Summary

```
S3 Landing (ins-xml-dev-landing)
    └── xml/*.xml              ← 30 generated XML files (10 policies × 3 transactions)
    └── scripts/*.py           ← Glue job script

AWS Glue Job: ins-xml-dev-xml-shredder
    └── Reads XML from landing → shreds into 8 Bronze Iceberg tables

S3 Bronze (ins-xml-dev-bronze)
    └── iceberg/               ← Iceberg table data (Parquet files)

Glue Data Catalog
    └── insurance_bronze       ← 8 Bronze tables (surrogate-key hierarchy)
    └── insurance_silver       ← 4 Silver SCD2 tables + 4 Gold tables (via dbt)

dbt Project: insurance_silver
    └── staging/               ← 7 views over Bronze
    └── silver/                ← 4 SCD2 tables
    └── gold/                  ← 2 aggregated reporting tables
```
