import logging
from typing import Dict, List

from helpers import safe_str
from s3_utils import list_xml_keys, read_xml_from_s3
from schemas import SCHEMAS
from iceberg_writer import write_iceberg_table

from builders.transaction_builder import build_policy_transaction
from builders.document_builder import build_object_documents, build_document_covered
from builders.policy_builder import build_policy
from builders.auto_builder import build_auto_policy
from builders.vehicle_builder import build_vehicles
from builders.registrant_builder import build_registrants
from builders.coverage_builder import build_coverages

logger = logging.getLogger(__name__)


def process_all_xml_files(spark, config) -> None:
    accumulator: Dict[str, List[Dict]] = {name: [] for name in SCHEMAS}

    xml_keys = list_xml_keys(config.source_bucket, prefix="xml/")
    if not xml_keys:
        logger.warning("No XML files found. Nothing to process.")
        return

    for key in xml_keys:
        source_file = key.split("/")[-1]
        logger.info("Processing file: %s", source_file)

        try:
            root = read_xml_from_s3(config.source_bucket, key)
        except Exception as exc:
            logger.exception("Failed to parse %s: %s", key, exc)
            continue

        txn_id = safe_str(root.get("transactionId")) or source_file

        accumulator["br_policy_transaction"].append(
            build_policy_transaction(root, source_file, config.load_ts)
        )
        accumulator["br_policy_transaction_object_document"].extend(
            build_object_documents(root, txn_id, source_file, config.load_ts)
        )
        accumulator["br_policy_transaction_object_document_covered"].extend(
            build_document_covered(root, txn_id, source_file, config.load_ts)
        )
        accumulator["br_policy_transaction_policy"].extend(
            build_policy(root, txn_id, source_file, config.load_ts)
        )
        accumulator["br_policy_auto"].extend(
            build_auto_policy(root, txn_id, source_file, config.load_ts)
        )
        accumulator["br_policy_auto_vehicle"].extend(
            build_vehicles(root, txn_id, source_file, config.load_ts)
        )
        accumulator["br_policy_vehicle_registrants"].extend(
            build_registrants(root, txn_id, source_file, config.load_ts)
        )
        accumulator["br_object_coverage_information"].extend(
            build_coverages(root, txn_id, source_file, config.load_ts)
        )

    for table_name, rows in accumulator.items():
        write_iceberg_table(
            spark=spark,
            rows=rows,
            schema=SCHEMAS[table_name],
            table_name=table_name,
            bronze_bucket=config.bronze_bucket,
            glue_database=config.glue_database,
        )

    logger.info("Shredding complete. Processed %d XML files.", len(xml_keys))
