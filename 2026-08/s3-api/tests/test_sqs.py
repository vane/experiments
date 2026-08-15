"""Pytest suite driving the SQS API with a real boto3 SQS client over HTTP.

Each test runs against a fresh in-process uvicorn server with an isolated
queue set (the module-level ``QUEUES`` dict is monkeypatched per test), so
runs are hermetic and never share state.  This mirrors tests/test_s3.py.

Run from the project root with the root on PYTHONPATH::

    PYTHONPATH=. pytest tests/test_sqs.py
"""

import hashlib
import queue
import socket
import threading
import time
import urllib.request

import boto3
import pytest
import uvicorn
from botocore.exceptions import ClientError

import aws.api.sqs_api as sqs_api
import aws.service.sqs as sqs_store

# QueueUrl host/path are just data to the API; the queue name is the last
# path segment.  A realistic SQS-style URL is used so tests don't depend on
# the local endpoint host.
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012"


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
def sqs(monkeypatch):
    # Hermetic state: a fresh isolated queue set per test.
    monkeypatch.setattr(sqs_store, "QUEUES", {"demo": queue.Queue(), "notes": queue.Queue()})
    monkeypatch.setattr(sqs_store, "_SEQUENCES", {})

    port = _free_port()
    config = uvicorn.Config(
        sqs_api.app, host="127.0.0.1", port=port,
        log_level="warning", access_log=False, lifespan="off",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_ready(port)

    client = boto3.client(
        "sqs",
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


# --- put message to queue (SendMessage) ---


def test_create_queue_and_send_message(sqs):
    created = sqs.create_queue(QueueName="new_orders")
    assert created["QueueUrl"].endswith("/new_orders")
    assert "new_orders" in sqs_store.QUEUES
    assert sqs_store.QUEUES["new_orders"].qsize() == 0

    # The returned URL routes back through SendMessage.
    sqs.send_message(QueueUrl=created["QueueUrl"], MessageBody="first")
    assert sqs_store.QUEUES["new_orders"].get_nowait() == "first"


def test_create_queue_name_exists(sqs):
    with pytest.raises(ClientError) as err:
        sqs.create_queue(QueueName="demo")  # already seeded by the fixture
    assert err.value.response["Error"]["Code"] == "QueueNameExists"


def test_create_queue_missing_name(sqs):
    with pytest.raises(ClientError) as err:
        sqs.create_queue(QueueName="")
    assert err.value.response["Error"]["Code"] == "MissingParameter"


def test_delete_queue(sqs):
    created = sqs.create_queue(QueueName="temp")
    sqs.send_message(QueueUrl=created["QueueUrl"], MessageBody="bye")
    assert "temp" in sqs_store.QUEUES

    sqs.delete_queue(QueueUrl=created["QueueUrl"])

    assert "temp" not in sqs_store.QUEUES
    with pytest.raises(ClientError) as err:
        sqs.send_message(QueueUrl=created["QueueUrl"], MessageBody="x")
    assert err.value.response["Error"]["Code"] == "QueueDoesNotExist"


def test_delete_queue_missing(sqs):
    with pytest.raises(ClientError) as err:
        sqs.delete_queue(QueueUrl=f"{QUEUE_URL}/ghost")
    assert err.value.response["Error"]["Code"] == "QueueDoesNotExist"


# --- put message to queue (SendMessage) ---
def test_send_message_puts_body_onto_queue(sqs):
    url = f"{QUEUE_URL}/demo"
    resp = sqs.send_message(QueueUrl=url, MessageBody="hello world")

    assert resp["MessageId"]
    assert resp["MD5OfMessageBody"] == hashlib.md5(b"hello world").hexdigest()

    # The message must actually be stored on the queue, in order.
    received = [sqs_store.QUEUES["demo"].get_nowait() for _ in range(sqs_store.QUEUES["demo"].qsize())]
    assert received == ["hello world"]
    assert sqs_store.QUEUES["notes"].qsize() == 0


def test_send_message_unique_ids_and_sequence(sqs):
    url = f"{QUEUE_URL}/demo"
    first = sqs.send_message(QueueUrl=url, MessageBody="a")
    second = sqs.send_message(QueueUrl=url, MessageBody="b")

    assert first["MessageId"] != second["MessageId"]
    assert int(first["SequenceNumber"]) < int(second["SequenceNumber"])


def test_send_message_preserves_fifo_order(sqs):
    url = f"{QUEUE_URL}/demo"
    bodies = [f"m{i}" for i in range(3)]
    for b in bodies:
        sqs.send_message(QueueUrl=url, MessageBody=b)

    received = [sqs_store.QUEUES["demo"].get_nowait() for _ in range(len(bodies))]
    assert received == bodies


def test_send_message_scoped_to_queue(sqs):
    sqs.send_message(QueueUrl=f"{QUEUE_URL}/notes", MessageBody="only notes")
    assert sqs_store.QUEUES["notes"].get_nowait() == "only notes"
    assert sqs_store.QUEUES["demo"].qsize() == 0


def test_send_message_missing_queue(sqs):
    with pytest.raises(ClientError) as err:
        sqs.send_message(QueueUrl=f"{QUEUE_URL}/nope", MessageBody="x")
    assert err.value.response["Error"]["Code"] == "QueueDoesNotExist"


def test_send_message_empty_body(sqs):
    with pytest.raises(ClientError) as err:
        sqs.send_message(QueueUrl=f"{QUEUE_URL}/demo", MessageBody="")
    assert err.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert sqs_store.QUEUES["demo"].qsize() == 0
