"""fs-lambda: boto3-facing FastAPI app for Lambda Invoke over Docker.

Exposes ``POST /2015-03-31/functions/{name}/invocations`` (the Lambda
rest-json ``Invoke`` protocol).  The function's container is run via the
Docker Engine API (see ``aws/service/lambda_service.py``) and its output is
returned as the invocation result.  Only Invoke is implemented.

The app is normally served through ``main.py``.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from aws.service.lambda_service import FunctionNotFound, invoke_function

app = FastAPI(title="fs-lambda")


@app.get("/")
async def health() -> JSONResponse:
    """Liveness probe (also used by the test harness readiness check)."""
    return JSONResponse({"status": "ok"})


@app.post("/2015-03-31/functions/{name}/invocations")
async def invoke(name: str, request: Request) -> Response:
    """Invoke a Lambda function by running its container."""
    payload = await request.body()
    try:
        output, exit_code = invoke_function(name, payload)
    except FunctionNotFound:
        body = {"__type": "ResourceNotFoundException",
                "message": f"Function not found: {name}"}
        return JSONResponse(
            body, status_code=404,
            media_type="application/json",
            headers={"x-amzn-errortype": "ResourceNotFoundException"},
        )
    headers = {}
    if exit_code != 0:
        headers["x-amz-function-error"] = "Unhandled"
    return Response(content=output, status_code=200, headers=headers)
