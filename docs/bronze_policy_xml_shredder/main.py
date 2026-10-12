import logging

from glue_job.bootstrap import init_glue_job
from orchestrator import process_all_xml_files

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    ctx = init_glue_job()
    process_all_xml_files(ctx["spark"], ctx["config"])
    ctx["job"].commit()
