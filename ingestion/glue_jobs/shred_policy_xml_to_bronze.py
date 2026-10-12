"""
shred_policy_xml_to_bronze.py
─────────────────────────────
AWS Glue 4.0 PySpark job.

Reads commercial-auto insurance XML files (policy_real_ex.xml schema),
shreds each node into its own Bronze Iceberg table, using surrogate keys
for parent-child relationships. Any node with id/code/value children
produces three columns: {node}_id, {node}_code, {node}_value.

Bronze table hierarchy
──────────────────────
  br_policy_transaction              ← root (1 row per XML file)
  br_policy_transaction_policy       ← child of PolicyTransaction
  br_policy_auto                     ← child of PolicyTransactionPolicy
  br_policy_auto_jurisdiction        ← child of PolicyAuto
  br_policy_auto_location            ← child of PolicyAutoJurisdiction
  br_policy_auto_vehicle             ← child of PolicyAuto (0..N per transaction)
  br_object_coverage_information     ← child of Jurisdiction OR Vehicle (0..N)
  br_object_coverage_attribute       ← child of ObjectCoverageInformation (0..N)

Surrogate keys
──────────────
  Every table has a UUID surrogate key (e.g. policy_transaction_sk).
  Child tables carry the parent's surrogate key as a foreign key.
  transaction_id (= filename without .xml) and policy_number are
  propagated to every table as root anchors for easy querying.

id / code / value pattern
──────────────────────────
  XML nodes containing <id>, <code>, <value> children are flattened
  into three columns:  {prefix}_id, {prefix}_code, {prefix}_value
  e.g. <EndorsementType> → endorsement_type_id / _code / _value

Idempotency
───────────
  transaction_id is checked against br_policy_transaction before processing.
  Files already loaded are skipped — safe to re-run without duplicates.

Job arguments
─────────────
  --SOURCE_BUCKET    S3 bucket for landing XMLs
  --BRONZE_BUCKET    S3 bucket for Iceberg table data
  --GLUE_DATABASE    Glue Data Catalog database name
"""

import sys
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import (
    StructType, StructField,
    StringType, TimestampType, DoubleType, IntegerType
)
import boto3
import xml.etree.ElementTree as ET

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Glue bootstrap ─────────────────────────────────────────────────────────────
args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "SOURCE_BUCKET", "BRONZE_BUCKET", "GLUE_DATABASE"],
)
sc           = SparkContext()
glue_ctx     = GlueContext(sc)
spark: SparkSession = glue_ctx.spark_session
job          = Job(glue_ctx)
job.init(args["JOB_NAME"], args)

SOURCE_BUCKET = args["SOURCE_BUCKET"]
BRONZE_BUCKET = args["BRONZE_BUCKET"]
GLUE_DATABASE = args["GLUE_DATABASE"]
LOAD_TS       = datetime.now(timezone.utc)

spark.conf.set("spark.sql.catalog.glue_catalog",
               "org.apache.iceberg.spark.SparkCatalog")
spark.conf.set("spark.sql.catalog.glue_catalog.catalog-impl",
               "org.apache.iceberg.aws.glue.GlueCatalog")
spark.conf.set("spark.sql.catalog.glue_catalog.io-impl",
               "org.apache.iceberg.aws.s3.S3FileIO")
spark.conf.set("spark.sql.catalog.glue_catalog.warehouse",
               f"s3://{BRONZE_BUCKET}/iceberg/")
spark.conf.set("spark.sql.defaultCatalog", "glue_catalog")


# ── Helpers ────────────────────────────────────────────────────────────────────

def sk() -> str:
    """Generate a new UUID surrogate key."""
    return str(uuid.uuid4())


def txt(el: Optional[ET.Element], tag: str) -> Optional[str]:
    """Return stripped text of a child tag, or None."""
    if el is None:
        return None
    node = el.find(tag)
    if node is None or not node.text:
        return None
    return node.text.strip() or None


def icv(el: Optional[ET.Element], tag: str, prefix: str) -> Dict[str, Optional[str]]:
    """
    For a node containing <id>, <code>, <value> children,
    return a dict with keys {prefix}_id, {prefix}_code, {prefix}_value.
    """
    child = el.find(tag) if el is not None else None
    return {
        f"{prefix}_id":    txt(child, "id"),
        f"{prefix}_code":  txt(child, "code"),
        f"{prefix}_value": txt(child, "value"),
    }


def safe_int(v: Optional[str]) -> Optional[int]:
    try:
        return int(v) if v else None
    except (TypeError, ValueError):
        return None


def safe_float(v: Optional[str]) -> Optional[float]:
    try:
        return float(v) if v else None
    except (TypeError, ValueError):
        return None


def audit(source_file: str) -> Dict:
    return {"source_file_name": source_file, "source_load_ts": LOAD_TS}


# ── S3 helpers ─────────────────────────────────────────────────────────────────

def list_xml_keys(bucket: str, prefix: str = "xml/") -> List[str]:
    s3        = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    keys      = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".xml"):
                keys.append(obj["Key"])
    logger.info("Found %d XML files in s3://%s/%s", len(keys), bucket, prefix)
    return keys


def read_xml(bucket: str, key: str) -> ET.Element:
    s3  = boto3.client("s3")
    raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    return ET.fromstring(raw)


def get_loaded_ids() -> set:
    try:
        rows = spark.sql(
            f"SELECT transaction_id FROM {GLUE_DATABASE}.br_policy_transaction"
        )
        ids = {r.transaction_id for r in rows.collect()}
        logger.info("%d transaction_ids already in Bronze.", len(ids))
        return ids
    except Exception:
        logger.info("br_policy_transaction not found — first run.")
        return set()


def write_iceberg(rows: List[Dict], schema: StructType, table: str) -> None:
    if not rows:
        logger.warning("No rows for %s — skipping.", table)
        return
    df: DataFrame = spark.createDataFrame(rows, schema=schema)
    df.write \
      .format("iceberg") \
      .mode("append") \
      .option("path", f"s3://{BRONZE_BUCKET}/iceberg/{table}") \
      .saveAsTable(f"{GLUE_DATABASE}.{table}")
    logger.info("Wrote %d rows → %s.%s", len(rows), GLUE_DATABASE, table)


# ── Row builders ───────────────────────────────────────────────────────────────

def build_policy_transaction(
    root: ET.Element, txn_id: str, source_file: str
) -> tuple:
    """
    br_policy_transaction — root node, 1 row per XML file.
    Returns (surrogate_key, row_dict).
    Captures all direct children of <PolicyTransaction> that are NOT
    PolicyTransactionPolicy (that goes in its own table).
    id/code/value nodes: countrynotunitedstateind, EndorsementType, TransactionType.
    """
    pt_sk = sk()
    row = {
        "policy_transaction_sk": pt_sk,
        "transaction_id":        txn_id,
        "policy_term_count":     safe_int(txt(root, "PolicyTermCount")),
        "rb_correlation_service_id": txt(root, "RBCorrelationServiceid"),
        "transaction_seq_num":   safe_int(txt(root, "TransactionSeqNum")),
        # id/code/value nodes
        **icv(root, "countrynotunitedstateind", "country_not_us_ind"),
        **icv(root, "EndorsementType",          "endorsement_type"),
        **icv(root, "TransactionType",          "transaction_type"),
        **audit(source_file),
    }
    return pt_sk, row


def build_policy_transaction_policy(
    root: ET.Element, pt_sk: str, txn_id: str, source_file: str
) -> tuple:
    """
    br_policy_transaction_policy — <PolicyTransactionPolicy> node.
    Returns (surrogate_key, row_dict, policy_number).
    id/code/value nodes: PrimaryRiskState.
    """
    pol = root.find("PolicyTransactionPolicy")
    ptp_sk = sk()
    policy_number = txt(pol, "PolicyNumber")
    row = {
        "policy_transaction_policy_sk": ptp_sk,
        "policy_transaction_sk":        pt_sk,
        "transaction_id":               txn_id,
        "policy_number":                policy_number,
        "agency_legal_name":            txt(pol, "AgencyLegalName"),
        "agency_number":                txt(pol, "AgencyNumber"),
        "inception_date":               txt(pol, "inceptionDate"),
        "naic_code":                    txt(pol, "NAICCode"),
        "policy_effective_date":        txt(pol, "PolicyEffectiveDate"),
        "policy_expiration_date":       txt(pol, "PolicyExpirationDate"),
        "quote_number":                 txt(pol, "QuoteNumber"),
        "term_effective_date":          txt(pol, "TermEffectiveDate"),
        "term_expiration_date":         txt(pol, "TermExpirationDate"),
        "transaction_completed_date":   txt(pol, "TransactionCompletedDate"),
        "transaction_effective_date":   txt(pol, "TransactionEffectiveDate"),
        # id/code/value
        **icv(pol, "PrimaryRiskState", "primary_risk_state"),
        **audit(source_file),
    }
    return ptp_sk, row, policy_number, pol


def build_policy_auto(
    pol: Optional[ET.Element], ptp_sk: str, txn_id: str, policy_number: str, source_file: str
) -> tuple:
    """
    br_policy_auto — <PolicyAuto> node inside PolicyTransactionPolicy.
    Returns (surrogate_key, row_dict, auto_element).
    """
    auto = pol.find("PolicyAuto") if pol is not None else None
    pa_sk = sk()
    row = {
        "policy_auto_sk":               pa_sk,
        "policy_transaction_policy_sk": ptp_sk,
        "transaction_id":               txn_id,
        "policy_number":                policy_number,
        "greatest_driver_number":       safe_int(txt(auto, "GreatestDriverNumber")),
        "greatest_vehicle_number":      safe_int(txt(auto, "GreatestVehicleNumber")),
        "total_number_of_drivers":      safe_int(txt(auto, "TotalNumberOfDrivers")),
        "total_number_of_vehicles":     safe_int(txt(auto, "TotalNumberOfVehicles")),
        "private_passenger_vehicle_count": safe_int(txt(auto, "PrivatePassengerVehicleCount")),
        **audit(source_file),
    }
    return pa_sk, row, auto


def build_policy_auto_jurisdiction(
    auto: Optional[ET.Element], pa_sk: str, txn_id: str, policy_number: str, source_file: str
) -> tuple:
    """
    br_policy_auto_jurisdiction — <PolicyAutoJurisdiction> node.
    id/code/value nodes: StateCode.
    Returns (surrogate_key, row_dict, juris_element).
    """
    juris = auto.find("PolicyAutoJurisdiction") if auto is not None else None
    paj_sk = sk()
    row = {
        "policy_auto_jurisdiction_sk": paj_sk,
        "policy_auto_sk":              pa_sk,
        "transaction_id":              txn_id,
        "policy_number":               policy_number,
        # id/code/value
        **icv(juris, "StateCode", "state_code"),
        **audit(source_file),
    }
    return paj_sk, row, juris


def build_policy_auto_location(
    juris: Optional[ET.Element], paj_sk: str, txn_id: str, policy_number: str, source_file: str
) -> Dict:
    """
    br_policy_auto_location — <PolicyAutoLocation> node.
    id/code/value nodes: Addressgroup.
    """
    loc = juris.find("PolicyAutoLocation") if juris is not None else None
    row = {
        "policy_auto_location_sk":     sk(),
        "policy_auto_jurisdiction_sk": paj_sk,
        "transaction_id":              txn_id,
        "policy_number":               policy_number,
        # id/code/value
        **icv(loc, "Addressgroup", "address_group"),
        "city_name":        txt(loc, "CityName"),
        "delivery_address": txt(loc, "DeliveryAddress"),
        "state":            txt(loc, "State"),
        "zip_code":         txt(loc, "ZipCode"),
        **audit(source_file),
    }
    return row


def build_coverage_information(
    cov_el: ET.Element,
    parent_sk: str,
    parent_type: str,       # 'jurisdiction' or 'vehicle'
    txn_id: str,
    policy_number: str,
    covered_item_identifier: Optional[str],
    source_file: str,
) -> tuple:
    """
    br_object_coverage_information — one row per <ObjectCoverageInformation>.
    parent_type indicates whether it belongs to a jurisdiction or vehicle.
    Returns (surrogate_key, row_dict).
    """
    oci_sk = sk()
    row = {
        "object_coverage_information_sk": oci_sk,
        "parent_sk":                      parent_sk,
        "parent_type":                    parent_type,
        "transaction_id":                 txn_id,
        "policy_number":                  policy_number,
        "covered_item_identifier":        covered_item_identifier,
        "coverage_change_type_code":      txt(cov_el, "CoverageChangeTypeCode"),
        "coverage_effective_date":        txt(cov_el, "CoverageEffectiveDate"),
        "coverage_expiration_date":       txt(cov_el, "CoverageExpirationDate"),
        "coverage_group_code":            txt(cov_el, "CoverageGroupCode"),
        "coverage_type":                  txt(cov_el, "CoverageType"),
        **audit(source_file),
    }
    return oci_sk, row


def build_coverage_attribute(
    attr_el: ET.Element,
    oci_sk: str,
    coverage_group_code: Optional[str],
    txn_id: str,
    policy_number: str,
    covered_item_identifier: Optional[str],
    source_file: str,
) -> Dict:
    """
    br_object_coverage_attribute — one row per <ObjectCoverageAttribute>.
    """
    return {
        "object_coverage_attribute_sk":   sk(),
        "object_coverage_information_sk": oci_sk,
        "transaction_id":                 txn_id,
        "policy_number":                  policy_number,
        "covered_item_identifier":        covered_item_identifier,
        "coverage_group_code":            coverage_group_code,
        "coverage_attribute_change_type_code": txt(attr_el, "CoverageAttributeChangeTypeCode"),
        "coverage_attribute_tag_name":    txt(attr_el, "CoverageAttributeTagName"),
        "coverage_attribute_type":        txt(attr_el, "CoverageAttributeType"),
        "coverage_attribute_value_text":  txt(attr_el, "CoverageAttributeValueText"),
        "coverage_attribute_value_number": safe_float(
            txt(attr_el, "CoverageAttributeValueNumber")
        ),
        **audit(source_file),
    }


def build_vehicle(
    veh_el: ET.Element, pa_sk: str, txn_id: str, policy_number: str, source_file: str
) -> tuple:
    """
    br_policy_auto_vehicle — one row per <PolicyAutoVehicle>.
    Returns (surrogate_key, row_dict, covered_item_identifier).
    """
    pav_sk = sk()
    cii    = txt(veh_el, "CoveredItemIdentifier")
    row = {
        "policy_auto_vehicle_sk": pav_sk,
        "policy_auto_sk":         pa_sk,
        "transaction_id":         txn_id,
        "policy_number":          policy_number,
        "covered_item_number":    safe_int(txt(veh_el, "CoveredItemNumber")),
        "covered_item_identifier": cii,
        "vehicle_change_type_code": txt(veh_el, "VehicleChangeTypeCode"),
        "busines_operation_group":  txt(veh_el, "BusinesOperationGroup"),
        "vehicle_type":           txt(veh_el, "VehicleType"),
        "vehicle_make":           txt(veh_el, "VehicleMake"),
        "vehicle_model":          txt(veh_el, "VehicleModel"),
        "vehicle_model_year":     safe_int(txt(veh_el, "VehicleModelyear")),
        **audit(source_file),
    }
    return pav_sk, row, cii


# ── Schemas ────────────────────────────────────────────────────────────────────
_S = StringType()
_T = TimestampType()
_D = DoubleType()
_I = IntegerType()

SCHEMAS: Dict[str, StructType] = {

    "br_policy_transaction": StructType([
        StructField("policy_transaction_sk",      _S),
        StructField("transaction_id",             _S),
        StructField("policy_term_count",          _I),
        StructField("rb_correlation_service_id",  _S),
        StructField("transaction_seq_num",        _I),
        # countrynotunitedstateind
        StructField("country_not_us_ind_id",      _S),
        StructField("country_not_us_ind_code",    _S),
        StructField("country_not_us_ind_value",   _S),
        # EndorsementType
        StructField("endorsement_type_id",        _S),
        StructField("endorsement_type_code",      _S),
        StructField("endorsement_type_value",     _S),
        # TransactionType
        StructField("transaction_type_id",        _S),
        StructField("transaction_type_code",      _S),
        StructField("transaction_type_value",     _S),
        StructField("source_file_name",           _S),
        StructField("source_load_ts",             _T),
    ]),

    "br_policy_transaction_policy": StructType([
        StructField("policy_transaction_policy_sk", _S),
        StructField("policy_transaction_sk",        _S),
        StructField("transaction_id",               _S),
        StructField("policy_number",                _S),
        StructField("agency_legal_name",            _S),
        StructField("agency_number",                _S),
        StructField("inception_date",               _S),
        StructField("naic_code",                    _S),
        StructField("policy_effective_date",        _S),
        StructField("policy_expiration_date",       _S),
        StructField("quote_number",                 _S),
        StructField("term_effective_date",          _S),
        StructField("term_expiration_date",         _S),
        StructField("transaction_completed_date",   _S),
        StructField("transaction_effective_date",   _S),
        # PrimaryRiskState
        StructField("primary_risk_state_id",        _S),
        StructField("primary_risk_state_code",      _S),
        StructField("primary_risk_state_value",     _S),
        StructField("source_file_name",             _S),
        StructField("source_load_ts",               _T),
    ]),

    "br_policy_auto": StructType([
        StructField("policy_auto_sk",               _S),
        StructField("policy_transaction_policy_sk", _S),
        StructField("transaction_id",               _S),
        StructField("policy_number",                _S),
        StructField("greatest_driver_number",       _I),
        StructField("greatest_vehicle_number",      _I),
        StructField("total_number_of_drivers",      _I),
        StructField("total_number_of_vehicles",     _I),
        StructField("private_passenger_vehicle_count", _I),
        StructField("source_file_name",             _S),
        StructField("source_load_ts",               _T),
    ]),

    "br_policy_auto_jurisdiction": StructType([
        StructField("policy_auto_jurisdiction_sk",  _S),
        StructField("policy_auto_sk",               _S),
        StructField("transaction_id",               _S),
        StructField("policy_number",                _S),
        # StateCode
        StructField("state_code_id",                _S),
        StructField("state_code_code",              _S),
        StructField("state_code_value",             _S),
        StructField("source_file_name",             _S),
        StructField("source_load_ts",               _T),
    ]),

    "br_policy_auto_location": StructType([
        StructField("policy_auto_location_sk",      _S),
        StructField("policy_auto_jurisdiction_sk",  _S),
        StructField("transaction_id",               _S),
        StructField("policy_number",                _S),
        # Addressgroup
        StructField("address_group_id",             _S),
        StructField("address_group_code",           _S),
        StructField("address_group_value",          _S),
        StructField("city_name",                    _S),
        StructField("delivery_address",             _S),
        StructField("state",                        _S),
        StructField("zip_code",                     _S),
        StructField("source_file_name",             _S),
        StructField("source_load_ts",               _T),
    ]),

    "br_policy_auto_vehicle": StructType([
        StructField("policy_auto_vehicle_sk",       _S),
        StructField("policy_auto_sk",               _S),
        StructField("transaction_id",               _S),
        StructField("policy_number",                _S),
        StructField("covered_item_number",          _I),
        StructField("covered_item_identifier",      _S),
        StructField("vehicle_change_type_code",     _S),
        StructField("busines_operation_group",      _S),
        StructField("vehicle_type",                 _S),
        StructField("vehicle_make",                 _S),
        StructField("vehicle_model",                _S),
        StructField("vehicle_model_year",           _I),
        StructField("source_file_name",             _S),
        StructField("source_load_ts",               _T),
    ]),

    "br_object_coverage_information": StructType([
        StructField("object_coverage_information_sk", _S),
        StructField("parent_sk",                    _S),
        StructField("parent_type",                  _S),   # 'jurisdiction' or 'vehicle'
        StructField("transaction_id",               _S),
        StructField("policy_number",                _S),
        StructField("covered_item_identifier",      _S),   # null for jurisdiction-level
        StructField("coverage_change_type_code",    _S),
        StructField("coverage_effective_date",      _S),
        StructField("coverage_expiration_date",     _S),
        StructField("coverage_group_code",          _S),
        StructField("coverage_type",                _S),
        StructField("source_file_name",             _S),
        StructField("source_load_ts",               _T),
    ]),

    "br_object_coverage_attribute": StructType([
        StructField("object_coverage_attribute_sk",   _S),
        StructField("object_coverage_information_sk", _S),
        StructField("transaction_id",                 _S),
        StructField("policy_number",                  _S),
        StructField("covered_item_identifier",        _S),
        StructField("coverage_group_code",            _S),
        StructField("coverage_attribute_change_type_code", _S),
        StructField("coverage_attribute_tag_name",    _S),
        StructField("coverage_attribute_type",        _S),
        StructField("coverage_attribute_value_text",  _S),
        StructField("coverage_attribute_value_number",_D),
        StructField("source_file_name",               _S),
        StructField("source_load_ts",                 _T),
    ]),
}


# ── Main processing loop ───────────────────────────────────────────────────────

def process_all_xml_files() -> None:
    loaded_ids = get_loaded_ids()
    xml_keys   = list_xml_keys(SOURCE_BUCKET, prefix="xml/")

    if not xml_keys:
        logger.warning("No XML files found — nothing to do.")
        return

    acc: Dict[str, List[Dict]] = {t: [] for t in SCHEMAS}
    skipped = processed = 0

    for key in xml_keys:
        source_file = key.split("/")[-1]
        txn_id      = source_file.replace(".xml", "").strip()

        if txn_id in loaded_ids:
            logger.info("Skip already-loaded: %s", txn_id)
            skipped += 1
            continue

        try:
            root = read_xml(SOURCE_BUCKET, key)
        except Exception as exc:
            logger.error("Parse error %s: %s", key, exc)
            continue

        processed += 1
        logger.info("Processing: %s", txn_id)

        # ── Layer 1: PolicyTransaction ────────────────────────────────────
        pt_sk, pt_row = build_policy_transaction(root, txn_id, source_file)
        acc["br_policy_transaction"].append(pt_row)

        # ── Layer 2: PolicyTransactionPolicy ─────────────────────────────
        ptp_sk, ptp_row, policy_number, pol_el = build_policy_transaction_policy(
            root, pt_sk, txn_id, source_file
        )
        acc["br_policy_transaction_policy"].append(ptp_row)

        # ── Layer 3: PolicyAuto ───────────────────────────────────────────
        pa_sk, pa_row, auto_el = build_policy_auto(
            pol_el, ptp_sk, txn_id, policy_number, source_file
        )
        acc["br_policy_auto"].append(pa_row)

        if auto_el is None:
            continue

        # ── Layer 4a: PolicyAutoJurisdiction ──────────────────────────────
        paj_sk, paj_row, juris_el = build_policy_auto_jurisdiction(
            auto_el, pa_sk, txn_id, policy_number, source_file
        )
        acc["br_policy_auto_jurisdiction"].append(paj_row)

        # ── Layer 5a: PolicyAutoLocation ──────────────────────────────────
        if juris_el is not None:
            acc["br_policy_auto_location"].append(
                build_policy_auto_location(
                    juris_el, paj_sk, txn_id, policy_number, source_file
                )
            )

            # ── Layer 6: Jurisdiction-level ObjectCoverageInformation ──────
            for cov_el in juris_el.findall("ObjectCoverageInformation"):
                grp = txt(cov_el, "CoverageGroupCode")
                oci_sk, oci_row = build_coverage_information(
                    cov_el, paj_sk, "jurisdiction",
                    txn_id, policy_number, None, source_file
                )
                acc["br_object_coverage_information"].append(oci_row)

                # ── Layer 7: ObjectCoverageAttribute (jurisdiction) ────────
                for attr_el in cov_el.findall("ObjectCoverageAttribute"):
                    acc["br_object_coverage_attribute"].append(
                        build_coverage_attribute(
                            attr_el, oci_sk, grp,
                            txn_id, policy_number, None, source_file
                        )
                    )

        # ── Layer 4b: PolicyAutoVehicle (0..N) ────────────────────────────
        for veh_el in auto_el.findall("PolicyAutoVehicle"):
            pav_sk, pav_row, cii = build_vehicle(
                veh_el, pa_sk, txn_id, policy_number, source_file
            )
            acc["br_policy_auto_vehicle"].append(pav_row)

            # ── Layer 5b: Vehicle-level ObjectCoverageInformation ──────────
            for cov_el in veh_el.findall("ObjectCoverageInformation"):
                grp = txt(cov_el, "CoverageGroupCode")
                oci_sk, oci_row = build_coverage_information(
                    cov_el, pav_sk, "vehicle",
                    txn_id, policy_number, cii, source_file
                )
                acc["br_object_coverage_information"].append(oci_row)

                # ── Layer 6b: ObjectCoverageAttribute (vehicle) ────────────
                for attr_el in cov_el.findall("ObjectCoverageAttribute"):
                    acc["br_object_coverage_attribute"].append(
                        build_coverage_attribute(
                            attr_el, oci_sk, grp,
                            txn_id, policy_number, cii, source_file
                        )
                    )

    logger.info("Scan complete — %d new, %d skipped.", processed, skipped)

    if processed == 0:
        logger.info("Bronze already up to date.")
        return

    for table, rows in acc.items():
        write_iceberg(rows, SCHEMAS[table], table)

    logger.info("Done. %d XML files loaded into Bronze.", processed)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    process_all_xml_files()
    job.commit()
