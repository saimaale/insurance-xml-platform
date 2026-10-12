# ---------------------------------------------------------------------------
# Athena Workgroup
# ---------------------------------------------------------------------------
resource "aws_athena_workgroup" "main" {
  name        = var.athena_workgroup_name
  description = "Insurance platform workgroup – results pinned to athena-results bucket."
  state       = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = var.athena_enforce_workgroup_config
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.athena_results_bucket_name}/query-results/"

      # Server-side encryption using S3-managed keys
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    # Engine version – Athena v3 supports Iceberg natively
    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }
}
