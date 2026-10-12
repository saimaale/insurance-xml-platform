# ---------------------------------------------------------------------------
# Locals – derive consistent name prefix used across all modules
# ---------------------------------------------------------------------------
locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# S3 Buckets
# ---------------------------------------------------------------------------
module "s3" {
  source = "./modules/s3"

  name_prefix                  = local.name_prefix
  bucket_suffix_source         = var.bucket_suffix_source
  bucket_suffix_landing        = var.bucket_suffix_landing
  bucket_suffix_bronze         = var.bucket_suffix_bronze
  bucket_suffix_silver         = var.bucket_suffix_silver
  bucket_suffix_athena_results = var.bucket_suffix_athena_results
}

# ---------------------------------------------------------------------------
# IAM Roles
# ---------------------------------------------------------------------------
module "iam" {
  source = "./modules/iam"

  name_prefix              = local.name_prefix
  bronze_bucket_arn        = module.s3.bronze_bucket_arn
  landing_bucket_arn       = module.s3.landing_bucket_arn
  silver_bucket_arn        = module.s3.silver_bucket_arn
  athena_results_bucket_arn = module.s3.athena_results_bucket_arn
  source_bucket_arn        = module.s3.source_bucket_arn
  glue_database_name       = var.glue_database_name
}

# ---------------------------------------------------------------------------
# Glue Data Catalog Database
# ---------------------------------------------------------------------------
module "glue" {
  source = "./modules/glue"

  name_prefix        = local.name_prefix
  glue_database_name = var.glue_database_name
  glue_role_arn      = module.iam.glue_role_arn
  landing_bucket     = module.s3.landing_bucket_name
  bronze_bucket      = module.s3.bronze_bucket_name
}

# ---------------------------------------------------------------------------
# Athena Workgroup
# ---------------------------------------------------------------------------
module "athena" {
  source = "./modules/athena"

  name_prefix                     = local.name_prefix
  athena_workgroup_name           = var.athena_workgroup_name
  athena_results_bucket_name      = module.s3.athena_results_bucket_name
  athena_enforce_workgroup_config = var.athena_enforce_workgroup_config
}

# ---------------------------------------------------------------------------
# DataSync (S3 source → S3 landing)
# ---------------------------------------------------------------------------
module "datasync" {
  source = "./modules/datasync"

  name_prefix              = local.name_prefix
  datasync_role_arn        = module.iam.datasync_role_arn
  source_bucket_arn        = module.s3.source_bucket_arn
  landing_bucket_arn       = module.s3.landing_bucket_arn
  source_bucket_name       = module.s3.source_bucket_name
  landing_bucket_name      = module.s3.landing_bucket_name

  # Wait for all IAM policies to be fully applied before DataSync runs its
  # access test — avoids race condition with IAM propagation delay
  depends_on = [module.iam]
}
