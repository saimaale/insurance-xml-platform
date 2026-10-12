# ---------------------------------------------------------------------------
# DataSync: S3 Source → S3 Landing
# ---------------------------------------------------------------------------

# Bucket policy: allow DataSync role to read from source bucket
resource "aws_s3_bucket_policy" "source" {
  bucket = var.source_bucket_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DataSyncReadSource"
        Effect = "Allow"
        Principal = {
          AWS = var.datasync_role_arn
        }
        Action = [
          "s3:GetObject",
          "s3:GetObjectTagging",
          "s3:GetObjectVersion",
          "s3:ListBucket",
          "s3:GetBucketLocation",
        ]
        Resource = [
          "arn:aws:s3:::${var.source_bucket_name}",
          "arn:aws:s3:::${var.source_bucket_name}/*",
        ]
      }
    ]
  })
}

# Bucket policy: allow DataSync role to read/write landing bucket
resource "aws_s3_bucket_policy" "landing" {
  bucket = var.landing_bucket_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DataSyncWriteLanding"
        Effect = "Allow"
        Principal = {
          AWS = var.datasync_role_arn
        }
        Action = [
          "s3:GetObject",
          "s3:GetObjectTagging",
          "s3:PutObject",
          "s3:PutObjectTagging",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:AbortMultipartUpload",
          "s3:ListMultipartUploadParts",
        ]
        Resource = [
          "arn:aws:s3:::${var.landing_bucket_name}",
          "arn:aws:s3:::${var.landing_bucket_name}/*",
        ]
      }
    ]
  })
}

# Source location (where inbound XMLs live)
resource "aws_datasync_location_s3" "source" {
  s3_bucket_arn = var.source_bucket_arn
  subdirectory  = "/inbound"

  s3_config {
    bucket_access_role_arn = var.datasync_role_arn
  }

  tags = { Name = "${var.name_prefix}-datasync-source" }
}

# Destination location (landing bucket)
resource "aws_datasync_location_s3" "landing" {
  s3_bucket_arn = var.landing_bucket_arn
  subdirectory  = "/xml"

  s3_config {
    bucket_access_role_arn = var.datasync_role_arn
  }

  tags = { Name = "${var.name_prefix}-datasync-landing" }
}

# Transfer task
resource "aws_datasync_task" "xml_copy" {
  name                     = "${var.name_prefix}-xml-copy"
  source_location_arn      = aws_datasync_location_s3.source.arn
  destination_location_arn = aws_datasync_location_s3.landing.arn

  options {
    verify_mode            = "ONLY_FILES_TRANSFERRED"
    overwrite_mode         = "NEVER"   # Don't overwrite if file already in landing
    atime                  = "BEST_EFFORT"
    mtime                  = "PRESERVE"
    uid                    = "NONE"
    gid                    = "NONE"
    preserve_deleted_files = "PRESERVE"
    posix_permissions      = "NONE"
    bytes_per_second       = -1        # No throttle
    task_queueing          = "ENABLED"
    log_level              = "OFF"
  }

  tags = { Name = "${var.name_prefix}-xml-copy" }
}
