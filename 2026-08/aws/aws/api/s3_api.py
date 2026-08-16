"""fs-s3: S3-compatible API over a CSV-backed local store.

The S3 routes live in ``aws.routes.s3``; this module only assembles the
FastAPI app and wires the router in.  The app is the boto3-facing
endpoint - point a client at ``endpoint_url`` with
``addressing_style="path"`` (see tests/test_s3.py).

The app is normally served through ``main.py``, which dispatches by
``x-amz-target`` to this app (S3) or to ``aws/api/sqs_api`` (SQS).
"""

from fastapi import FastAPI

from aws.routes.s3 import router as s3_router

app = FastAPI(title="fs-s3")
app.include_router(s3_router)
