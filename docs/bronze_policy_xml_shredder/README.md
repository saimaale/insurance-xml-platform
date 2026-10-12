# Bronze Policy XML Shredder

This project refactors the Glue job into multiple files grouped by responsibility.

## How Glue runs this
Glue still runs **one entry file only**: `main.py`.

That file initializes Glue/Spark and then calls the orchestrator, which imports and executes the rest of the modules.

## Suggested Glue Python script path
Upload this folder to S3 and point the Glue job script to:

`main.py`

## Job arguments
- `--JOB_NAME`
- `--SOURCE_BUCKET`
- `--BRONZE_BUCKET`
- `--GLUE_DATABASE`

## Local structure
```text
bronze_policy_xml_shredder/
├── main.py
├── config.py
├── helpers.py
├── schemas.py
├── s3_utils.py
├── iceberg_writer.py
├── orchestrator.py
├── builders/
│   ├── __init__.py
│   ├── auto_builder.py
│   ├── coverage_builder.py
│   ├── document_builder.py
│   ├── policy_builder.py
│   ├── registrant_builder.py
│   ├── transaction_builder.py
│   └── vehicle_builder.py
└── glue_job/
    ├── __init__.py
    └── bootstrap.py
```
