# ---------------------------------------------------------------------------
# Global
# ---------------------------------------------------------------------------
variable "project_name" {
  description = "Short project identifier used as a prefix for all resource names."
  type        = string
  default     = "ins-xml"
}

variable "environment" {
  description = "Deployment environment (dev / staging / prod)."
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Named AWS CLI profile to use for authentication."
  type        = string
  default     = "default"
}

# ---------------------------------------------------------------------------
# S3 bucket name suffixes
# Override these if you need globally unique names (they are appended to
# "<project_name>-<environment>-<suffix>").
# ---------------------------------------------------------------------------
variable "bucket_suffix_source" {
  description = "Suffix for the raw inbound XML source bucket."
  type        = string
  default     = "source"
}

variable "bucket_suffix_landing" {
  description = "Suffix for the DataSync landing bucket."
  type        = string
  default     = "landing"
}

variable "bucket_suffix_bronze" {
  description = "Suffix for the Bronze Iceberg table data bucket."
  type        = string
  default     = "bronze"
}

variable "bucket_suffix_silver" {
  description = "Suffix for the Silver / dbt output bucket."
  type        = string
  default     = "silver"
}

variable "bucket_suffix_athena_results" {
  description = "Suffix for the Athena query results bucket."
  type        = string
  default     = "athena-results"
}

# ---------------------------------------------------------------------------
# Glue
# ---------------------------------------------------------------------------
variable "glue_database_name" {
  description = "Name of the Glue Data Catalog database."
  type        = string
  default     = "insurance_bronze"
}

# ---------------------------------------------------------------------------
# Athena
# ---------------------------------------------------------------------------
variable "athena_workgroup_name" {
  description = "Name of the Athena workgroup."
  type        = string
  default     = "insurance-wg"
}

variable "athena_enforce_workgroup_config" {
  description = "Prevent queries from overriding workgroup result location."
  type        = bool
  default     = true
}
