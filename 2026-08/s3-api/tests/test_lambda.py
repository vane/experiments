"""Pytest suite driving the Lambda API with a real boto3 Lambda client over HTTP.

Each test boots a fresh in-process uvicorn server and runs the function's
container via the Docker Engine API (podman-compatible socket); the
registered image set (``aws.service.lambda_service.FUNCTIONS``) is
monkeypatched per test so runs are hermetic.  Requires a running Docker /
podman daemon with the ``alpine`` image present.

Run from the project root with the root on PYTHONPATH::

    PYTHONPATH=. pytest tests/test_lambda.py
"""

import socket
import threading
import time
import urllib.request

import boto3
import pytest
import uvicorn
from botocore.exceptions import ClientError

import aws.api.lambda_api as lambda_api
import aws.service.lambda_service as lambda_service

# A tiny local image that runs an arbitrary shell command.
IMAGE = "alpine"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.5) as resp:
                if resp.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("server did not become ready")


@pytest.fixture
def lamb(monkeypatch):
    # Hermetic state: a fresh isolated function set per test.
    monkeypatch.setattr(lambda_service, "FUNCTIONS", {})

    port = _free_port()
    config = uvicorn.Config(
        lambda_api.app, host="127.0.0.1", port=port,
        log_level="warning", access_log=False, lifespan="off",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_ready(port)

    client = boto3.client(
        "lambda",
        endpoint_url=f"http://127.0.0.1:{port}",
        aws_access_key_id="test",
        aws_secret_access_key="test",  # accepted but not verified
        region_name="us-east-1",
    )
    try:
        yield client
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def test_invoke_returns_output(lamb):
    lambda_service.FUNCTIONS["hello"] = {
        "image": IMAGE,
        "Cmd": ["/bin/sh", "-c", "echo hello-lambda"],
    }
    resp = lamb.invoke(FunctionName="hello", Payload=b'{"a": 1}')

    assert resp["StatusCode"] == 200
    assert resp.get("FunctionError") is None
    assert resp["Payload"].read() == b"hello-lambda"


def test_invoke_function_error(lamb):
    lambda_service.FUNCTIONS["boom"] = {
        "image": IMAGE,
        "Cmd": ["/bin/sh", "-c", "echo oops; exit 1"],
    }
    resp = lamb.invoke(FunctionName="boom", Payload=b"{}")

    assert resp["StatusCode"] == 200
    assert resp["FunctionError"] == "Unhandled"
    assert resp["Payload"].read() == b"oops"


def test_invoke_missing_function(lamb):
    with pytest.raises(ClientError) as err:
        lamb.invoke(FunctionName="nope", Payload=b"{}")
    assert err.value.response["Error"]["Code"] == "ResourceNotFoundException"
