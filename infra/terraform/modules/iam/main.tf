# ---------------------------------------------------------------------------
# Glue Execution Role
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = "${var.name_prefix}-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

# Attach AWS-managed Glue service policy (CloudWatch Logs, etc.)
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Inline policy: S3 access for Glue (landing R/O, bronze R/W, silver R/W, athena-results R/W)
data "aws_iam_policy_document" "glue_s3" {
  # Read source XMLs from the landing bucket
  statement {
    sid     = "ReadLanding"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      var.landing_bucket_arn,
      "${var.landing_bucket_arn}/*",
    ]
  }

  # Full access to bronze bucket (Iceberg table data)
  statement {
    sid     = "ReadWriteBronze"
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [
      var.bronze_bucket_arn,
      "${var.bronze_bucket_arn}/*",
    ]
  }

  # Full access to silver bucket
  statement {
    sid     = "ReadWriteSilver"
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [
      var.silver_bucket_arn,
      "${var.silver_bucket_arn}/*",
    ]
  }

  # Write Athena query results (needed when Glue calls Athena)
  statement {
    sid     = "WriteAthenaResults"
    actions = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = [
      var.athena_results_bucket_arn,
      "${var.athena_results_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "glue_s3" {
  name   = "${var.name_prefix}-glue-s3-policy"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_s3.json
}

# Glue Data Catalog permissions
data "aws_iam_policy_document" "glue_catalog" {
  statement {
    sid = "GlueCatalogAccess"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:DeleteTable",
      "glue:BatchCreatePartition",
      "glue:CreatePartition",
      "glue:UpdatePartition",
      "glue:DeletePartition",
    ]
    resources = ["*"]
  }

  # Athena access so the Glue job can run validation queries
  statement {
    sid = "AthenaQueryAccess"
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "glue_catalog" {
  name   = "${var.name_prefix}-glue-catalog-policy"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_catalog.json
}


# ---------------------------------------------------------------------------
# DataSync Role
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "datasync_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["datasync.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "datasync" {
  name               = "${var.name_prefix}-datasync-role"
  assume_role_policy = data.aws_iam_policy_document.datasync_assume_role.json
}

data "aws_iam_policy_document" "datasync_s3" {
  # Read from source bucket
  statement {
    sid     = "ReadSource"
    actions = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
    resources = [
      var.source_bucket_arn,
      "${var.source_bucket_arn}/*",
    ]
  }

  # Write to landing bucket
  statement {
    sid     = "WriteLanding"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
    ]
    resources = [
      var.landing_bucket_arn,
      "${var.landing_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "datasync_s3" {
  name   = "${var.name_prefix}-datasync-s3-policy"
  role   = aws_iam_role.datasync.id
  policy = data.aws_iam_policy_document.datasync_s3.json
}
