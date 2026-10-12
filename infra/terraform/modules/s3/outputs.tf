output "source_bucket_name"         { value = aws_s3_bucket.buckets["source"].bucket }
output "landing_bucket_name"        { value = aws_s3_bucket.buckets["landing"].bucket }
output "bronze_bucket_name"         { value = aws_s3_bucket.buckets["bronze"].bucket }
output "silver_bucket_name"         { value = aws_s3_bucket.buckets["silver"].bucket }
output "athena_results_bucket_name" { value = aws_s3_bucket.buckets["athena_results"].bucket }

output "source_bucket_arn"         { value = aws_s3_bucket.buckets["source"].arn }
output "landing_bucket_arn"        { value = aws_s3_bucket.buckets["landing"].arn }
output "bronze_bucket_arn"         { value = aws_s3_bucket.buckets["bronze"].arn }
output "silver_bucket_arn"         { value = aws_s3_bucket.buckets["silver"].arn }
output "athena_results_bucket_arn" { value = aws_s3_bucket.buckets["athena_results"].arn }
