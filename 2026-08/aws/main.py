"""fs-aws: a single FastAPI entrypoint that dispatches to the S3 or SQS app.

boto3 talks two very different protocols to the services in this repo:

* SQS (``aws/api/sqs_api.py``) uses the AWS JSON 1.0 protocol — every call is a
  POST to ``/`` carrying an ``X-Amz-Target`` header (e.g.
  ``AmazonSQS.SendMessage``).
* S3 (``aws/api/s3_api.py``) is path-based (``PUT /bucket/key`` …) and never sends a
  target header.

This module inspects ``x-amz-target`` and forwards each request to the
matching app, so a single endpoint can serve both boto3 clients.

Run (from this directory)::

    uvicorn main:app --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from aws.api.lambda_api import app as lambda_app
from aws.api.s3_api import app as s3_app
from aws.api.sqs_api import app as sqs_app

app = FastAPI(title="fs-aws")


class _DispatchMiddleware:
    """Route HTTP requests by ``X-Amz-Target`` or URL path.

    A target header means an SQS call (send to the SQS app).  Lambda's
    rest-json protocol is path-based under ``/2015-03-31/``; those go to the
    Lambda app.  Anything else is treated as S3 (path-based, send to the S3
    app).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app  # outer FastAPI app (handles non-HTTP scopes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            # ASGI header keys are lower-cased bytes.
            headers = dict(scope.get("headers", []))
            if headers.get(b"x-amz-target"):
                await sqs_app(scope, receive, send)
                return
            if scope.get("path", "").startswith("/2015-03-31/"):
                await lambda_app(scope, receive, send)
                return
            await s3_app(scope, receive, send)
            return
        await self.app(scope, receive, send)


app.add_middleware(_DispatchMiddleware)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
