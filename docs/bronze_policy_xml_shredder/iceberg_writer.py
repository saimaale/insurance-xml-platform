import logging
from typing import List, Dict, Any
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType

logger = logging.getLogger(__name__)


def write_iceberg_table(
    spark: SparkSession,
    rows: List[Dict[str, Any]],
    schema: StructType,
    table_name: str,
    bronze_bucket: str,
    glue_database: str,
) -> None:
    if not rows:
        logger.warning("No rows to write for table %s. Skipping.", table_name)
        return

    df: DataFrame = spark.createDataFrame(rows, schema=schema)
    table_location = f"s3://{bronze_bucket}/iceberg/{table_name}"

    df.write \
        .format("iceberg") \
        .mode("append") \
        .option("path", table_location) \
        .saveAsTable(f"{glue_database}.{table_name}")

    logger.info("Wrote %d rows to %s.%s", len(rows), glue_database, table_name)
