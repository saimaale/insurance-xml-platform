variable "name_prefix"               { type = string }
variable "landing_bucket_arn"         { type = string }
variable "bronze_bucket_arn"          { type = string }
variable "silver_bucket_arn"          { type = string }
variable "athena_results_bucket_arn"  { type = string }
variable "source_bucket_arn"          { type = string }
variable "glue_database_name"         { type = string }
