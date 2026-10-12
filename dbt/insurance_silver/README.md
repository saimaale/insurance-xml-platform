# insurance_silver — dbt Project

Transforms Bronze Iceberg tables (shredded from insurance XMLs) into clean,
tested Silver analytics entities using dbt on AWS Athena (Engine V3).

## Layer Architecture

```
S3 XMLs → [Glue Shredder] → Bronze Iceberg → [dbt/Athena] → Silver Iceberg
```

## Models

### Staging (views over Bronze)
| Model | Source Table | Purpose |
|---|---|---|
| stg_br_policy_transaction | br_policy_transaction | Transaction header + clean date casts |
| stg_br_policy_auto | br_policy_auto | Named insured + policy dates |
| stg_br_policy_auto_vehicle | br_policy_auto_vehicle | Vehicle attributes + integer year |
| stg_br_policy_vehicle_registrants | br_policy_vehicle_registrants | Driver info + date of birth |
| stg_br_object_coverage_information | br_object_coverage_information | Coverage lines + decimal amounts |

### Silver (Iceberg tables)
| Model | Grain | Key Use Case |
|---|---|---|
| sl_policy | transaction_id | Policy-level reporting |
| sl_vehicle | (transaction_id, vehicle_id) | Fleet/vehicle analysis |
| sl_vehicle_coverage | (transaction_id, vehicle_id, coverage_code) | Premium aggregation |
| sl_vehicle_registrant | (transaction_id, vehicle_id, registrant_name) | Driver/risk analysis |

## Setup

### 1. Install dependencies
```bash
cd dbt/insurance_silver
pip install dbt-athena-community
dbt deps
```

### 2. Configure AWS connection
Copy `profiles.yml` to `~/.dbt/profiles.yml` and update:
- `region_name` — your AWS region
- `s3_staging_dir` — your Athena results bucket path
- `aws_profile_name` — your AWS CLI profile

### 3. Run models
```bash
# Test connection
dbt debug

# Run all models
dbt run

# Run only Silver models
dbt run --select silver

# Run tests
dbt test

# Run and test together
dbt build
```

### 4. View docs
```bash
dbt docs generate
dbt docs serve
```
Then open http://localhost:8080

## Tests Included
- `not_null` on all key columns
- `unique` on primary keys (transaction_id in sl_policy)
- `relationships` — vehicle/registrant/coverage rows reference valid sl_policy rows
- `accepted_values` — vehicle_type and coverage_code are constrained to known values
