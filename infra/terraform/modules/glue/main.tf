# ---------------------------------------------------------------------------
# Glue Data Catalog Database
# ---------------------------------------------------------------------------
resource "aws_glue_catalog_database" "bronze" {
  name        = var.glue_database_name
  description = "Bronze layer: raw Iceberg tables shredded from insurance XMLs."
}

# ---------------------------------------------------------------------------
# Glue ETL Job (placeholder – script uploaded separately after repo is wired)
# ---------------------------------------------------------------------------
resource "aws_glue_job" "xml_shredder" {
  name         = "${var.name_prefix}-xml-shredder"
  role_arn     = var.glue_role_arn
  glue_version = "4.0"

  command {
    name            = "glueetl"
    script_location = "s3://${var.landing_bucket}/scripts/shred_policy_xml_to_bronze.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "true"
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://${var.bronze_bucket}/spark-logs/"
    "--TempDir"                          = "s3://${var.bronze_bucket}/tmp/"
    "--SOURCE_BUCKET"                    = var.landing_bucket
    "--BRONZE_BUCKET"                    = var.bronze_bucket
    "--GLUE_DATABASE"                    = var.glue_database_name
    "--databaseName"                     = var.glue_database_name
    # Enable native Iceberg support in Glue 4.0
    "--datalake-formats"                 = "iceberg"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  # Keep worker count minimal for a portfolio / learning project
  worker_type       = "G.1X"
  number_of_workers = 2

  # Automatically clean up bookmarks between runs during development
  # Switch to SYNC_ONLY for incremental loads once stable
  max_retries = 0
}
