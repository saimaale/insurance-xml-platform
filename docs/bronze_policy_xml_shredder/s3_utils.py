import logging
from typing import List
import boto3
import xml.etree.ElementTree as etree

logger = logging.getLogger(__name__)


def list_xml_keys(bucket: str, prefix: str = "xml/") -> List[str]:
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    keys = []

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".xml"):
                keys.append(obj["Key"])

    logger.info("Found %d XML files in s3://%s/%s", len(keys), bucket, prefix)
    return keys


def read_xml_from_s3(bucket: str, key: str) -> etree.Element:
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read()
    return etree.fromstring(content)
