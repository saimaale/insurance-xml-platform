import sys
import logging
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

from config import build_config

logger = logging.getLogger(__name__)


def init_glue_job():
    args = getResolvedOptions(
        sys.argv,
        ["JOB_NAME", "SOURCE_BUCKET", "BRONZE_BUCKET", "GLUE_DATABASE"],
    )

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    config = build_config(args)

    spark.conf.set("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
    spark.conf.set("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
    spark.conf.set("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    spark.conf.set("spark.sql.catalog.glue_catalog.warehouse", f"s3://{config.bronze_bucket}/iceberg/")
    spark.conf.set("spark.sql.defaultCatalog", "glue_catalog")

    logger.info("Glue job initialized for database: %s", config.glue_database)

    return {
        "args": args,
        "glue_context": glue_context,
        "spark": spark,
        "job": job,
        "config": config,
    }
