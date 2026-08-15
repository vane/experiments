"""fs-sqs: a minimal SQS-compatible API (boto3-compatible) over in-process queues.

Implements ``SendMessage``, ``CreateQueue`` and ``DeleteQueue``:
``SendMessage`` accepts a ``MessageBody`` and puts it onto a named in-process
queue (``queue.Queue``); ``CreateQueue`` / ``DeleteQueue`` add and remove the
queue.  The queue store and operations live in ``aws.service.sqs``; this
module only exposes them as a boto3-facing FastAPI app.

The app is normally served through ``main.py``, which dispatches by
``x-amz-target`` to this app (SQS) or to ``aws/api/s3_api`` (S3).
"""

from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aws.service.sqs import create_queue, delete_queue, error_response, send_message

app = FastAPI(title="fs-sqs")


async def _load_body(request: Request) -> dict | JSONResponse:
    """Parse the JSON payload, or return an error response for malformed JSON."""
    try:
        return json.loads(await request.body())
    except json.JSONDecodeError:
        return error_response("InvalidParameterValue", "The request body is not valid JSON.")


@app.get("/")
async def health() -> JSONResponse:
    """Liveness probe (also used by the test harness readiness check)."""
    return JSONResponse({"status": "ok"})


@app.post("/")
async def api(request: Request) -> JSONResponse:
    """Dispatch SQS operations (SendMessage, CreateQueue, DeleteQueue)."""
    match request.headers.get("x-amz-target", ""):
        case "AmazonSQS.SendMessage":
            payload = await _load_body(request)
            if isinstance(payload, JSONResponse):
                return payload
            return send_message(payload)
        case "AmazonSQS.CreateQueue":
            payload = await _load_body(request)
            if isinstance(payload, JSONResponse):
                return payload
            return create_queue(payload, str(request.base_url))
        case "AmazonSQS.DeleteQueue":
            payload = await _load_body(request)
            if isinstance(payload, JSONResponse):
                return payload
            return delete_queue(payload)
        case target:
            return error_response("UnknownOperation", f"Unsupported SQS operation: {target}.")
