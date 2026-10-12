# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------
locals {
  buckets = {
    source         = "${var.name_prefix}-${var.bucket_suffix_source}"
    landing        = "${var.name_prefix}-${var.bucket_suffix_landing}"
    bronze         = "${var.name_prefix}-${var.bucket_suffix_bronze}"
    silver         = "${var.name_prefix}-${var.bucket_suffix_silver}"
    athena_results = "${var.name_prefix}-${var.bucket_suffix_athena_results}"
  }
}

# ---------------------------------------------------------------------------
# Buckets
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "buckets" {
  for_each = local.buckets
  bucket   = each.value
}

# Block all public access on every bucket
resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = local.buckets

  bucket                  = aws_s3_bucket.buckets[each.key].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning on source and landing so files can be recovered
resource "aws_s3_bucket_versioning" "source" {
  bucket = aws_s3_bucket.buckets["source"].id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_versioning" "landing" {
  bucket = aws_s3_bucket.buckets["landing"].id
  versioning_configuration { status = "Enabled" }
}

# Lifecycle rule: auto-expire Athena result files after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.buckets["athena_results"].id

  rule {
    id     = "expire-athena-results"
    status = "Enabled"
    filter {}
    expiration { days = 30 }
  }
}
