# ---------------------------------------------------------------------------
# S3 Bucket names  (use these in Glue jobs, dbt profiles, etc.)
# ---------------------------------------------------------------------------
output "source_bucket_name" {
  description = "S3 bucket for inbound raw XMLs."
  value       = module.s3.source_bucket_name
}

output "landing_bucket_name" {
  description = "S3 bucket where DataSync deposits copied XMLs."
  value       = module.s3.landing_bucket_name
}

output "bronze_bucket_name" {
  description = "S3 bucket backing the Bronze Iceberg tables."
  value       = module.s3.bronze_bucket_name
}

output "silver_bucket_name" {
  description = "S3 bucket for dbt / Silver output."
  value       = module.s3.silver_bucket_name
}

output "athena_results_bucket_name" {
  description = "S3 bucket for Athena query results."
  value       = module.s3.athena_results_bucket_name
}

# ---------------------------------------------------------------------------
# IAM Role ARNs  (needed when configuring Glue jobs and DataSync)
# ---------------------------------------------------------------------------
output "glue_role_arn" {
  description = "ARN of the IAM role used by Glue ETL jobs."
  value       = module.iam.glue_role_arn
}

output "datasync_role_arn" {
  description = "ARN of the IAM role used by DataSync."
  value       = module.iam.datasync_role_arn
}

# ---------------------------------------------------------------------------
# Glue Catalog
# ---------------------------------------------------------------------------
output "glue_database_name" {
  description = "Name of the Glue Data Catalog database."
  value       = module.glue.glue_database_name
}

# ---------------------------------------------------------------------------
# Athena
# ---------------------------------------------------------------------------
output "athena_workgroup_name" {
  description = "Name of the Athena workgroup."
  value       = module.athena.athena_workgroup_name
}
