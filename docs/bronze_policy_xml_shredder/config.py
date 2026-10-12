from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class JobConfig:
    job_name: str
    source_bucket: str
    bronze_bucket: str
    glue_database: str
    load_ts: datetime


def build_config(args: dict) -> JobConfig:
    return JobConfig(
        job_name=args["JOB_NAME"],
        source_bucket=args["SOURCE_BUCKET"],
        bronze_bucket=args["BRONZE_BUCKET"],
        glue_database=args["GLUE_DATABASE"],
        load_ts=datetime.now(timezone.utc),
    )
