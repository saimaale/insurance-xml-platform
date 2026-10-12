output "glue_database_name" { value = aws_glue_catalog_database.bronze.name }
output "glue_job_name"      { value = aws_glue_job.xml_shredder.name }
