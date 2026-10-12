output "datasync_task_arn"           { value = aws_datasync_task.xml_copy.arn }
output "datasync_source_location_arn" { value = aws_datasync_location_s3.source.arn }
output "datasync_landing_location_arn"{ value = aws_datasync_location_s3.landing.arn }
