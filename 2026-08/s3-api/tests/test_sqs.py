"""Pytest suite driving the SQS API with a real boto3 SQS client over HTTP.

Each test runs against a fresh in-process uvicorn server with an isolated
queue set (the module-level ``QUEUES`` dict is monkeypatched per test), so
runs are hermetic and never share state.  This mirrors tests/test_s3.py.

Covers the visibility-timeout lifecycle (receive -> hidden -> redelivered,
change visibility, delete) and dead-letter-queue redrive via a
``RedrivePolicy`` on the source queue.

Run from the project root with the root on PYTHONPATH::

    PYTHONPATH=. pytest tests/test_sqs.py
"""

import hashlib
import json
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
    monkeypatch.setattr(sqs_store, "QUEUES", {"demo": sqs_store.Queue("demo"), "notes": sqs_store.Queue("notes")})

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


# --- create / delete queue ---


def test_create_queue(sqs):
    created = sqs.create_queue(QueueName="new_orders")
    assert created["QueueUrl"].endswith("/new_orders")
    assert "new_orders" in sqs_store.QUEUES


def test_create_queue_with_visibility_timeout_attribute(sqs):
    created = sqs.create_queue(QueueName="tuned", Attributes={"VisibilityTimeout": "45"})
    attrs = sqs.get_queue_attributes(QueueUrl=created["QueueUrl"], AttributeNames=["VisibilityTimeout"])["Attributes"]
    assert attrs["VisibilityTimeout"] == "45"


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


# --- send ---


def test_send_message(sqs):
    resp = sqs.send_message(QueueUrl=f"{QUEUE_URL}/demo", MessageBody="hello world")
    assert resp["MessageId"]
    assert resp["MD5OfMessageBody"] == hashlib.md5(b"hello world").hexdigest()


def test_send_message_unique_ids_and_sequence(sqs):
    url = f"{QUEUE_URL}/demo"
    first = sqs.send_message(QueueUrl=url, MessageBody="a")
    second = sqs.send_message(QueueUrl=url, MessageBody="b")
    assert first["MessageId"] != second["MessageId"]
    assert int(first["SequenceNumber"]) < int(second["SequenceNumber"])


def test_send_message_missing_queue(sqs):
    with pytest.raises(ClientError) as err:
        sqs.send_message(QueueUrl=f"{QUEUE_URL}/nope", MessageBody="x")
    assert err.value.response["Error"]["Code"] == "QueueDoesNotExist"


def test_send_message_empty_body(sqs):
    with pytest.raises(ClientError) as err:
        sqs.send_message(QueueUrl=f"{QUEUE_URL}/demo", MessageBody="")
    assert err.value.response["Error"]["Code"] == "InvalidParameterValue"


# --- receive + visibility timeout ---


def test_receive_fifo_order(sqs):
    url = f"{QUEUE_URL}/demo"
    bodies = [f"m{i}" for i in range(3)]
    for b in bodies:
        sqs.send_message(QueueUrl=url, MessageBody=b)

    resp = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=3)
    assert [m["Body"] for m in resp["Messages"]] == bodies
    assert all(m["Attributes"]["ApproximateReceiveCount"] == "1" for m in resp["Messages"])


def test_receive_scoped_to_queue(sqs):
    sqs.send_message(QueueUrl=f"{QUEUE_URL}/notes", MessageBody="only notes")

    assert "Messages" not in sqs.receive_message(QueueUrl=f"{QUEUE_URL}/demo")
    resp = sqs.receive_message(QueueUrl=f"{QUEUE_URL}/notes")
    assert [m["Body"] for m in resp["Messages"]] == ["only notes"]


def test_receive_missing_queue(sqs):
    with pytest.raises(ClientError) as err:
        sqs.receive_message(QueueUrl=f"{QUEUE_URL}/nope")
    assert err.value.response["Error"]["Code"] == "QueueDoesNotExist"


def test_received_message_hidden_until_visibility_timeout(sqs):
    url = f"{QUEUE_URL}/demo"
    sqs.send_message(QueueUrl=url, MessageBody="sleeper")

    first = sqs.receive_message(QueueUrl=url, VisibilityTimeout=1)
    assert len(first["Messages"]) == 1

    # While in flight the message is invisible to further receives.
    assert "Messages" not in sqs.receive_message(QueueUrl=url)

    time.sleep(1.1)
    second = sqs.receive_message(QueueUrl=url)
    assert len(second["Messages"]) == 1
    # Redelivered: same message, second receive, fresh receipt handle.
    assert second["Messages"][0]["MessageId"] == first["Messages"][0]["MessageId"]
    assert second["Messages"][0]["Attributes"]["ApproximateReceiveCount"] == "2"
    assert second["Messages"][0]["ReceiptHandle"] != first["Messages"][0]["ReceiptHandle"]


def test_change_message_visibility(sqs):
    url = f"{QUEUE_URL}/demo"
    sqs.send_message(QueueUrl=url, MessageBody="stretched")

    first = sqs.receive_message(QueueUrl=url, VisibilityTimeout=10)
    handle = first["Messages"][0]["ReceiptHandle"]
    assert "Messages" not in sqs.receive_message(QueueUrl=url)

    # Cancelling the timeout (0) makes the message visible again.
    sqs.change_message_visibility(QueueUrl=url, ReceiptHandle=handle, VisibilityTimeout=0)
    assert len(sqs.receive_message(QueueUrl=url)["Messages"]) == 1


def test_change_message_visibility_invalid_handle(sqs):
    with pytest.raises(ClientError) as err:
        sqs.change_message_visibility(QueueUrl=f"{QUEUE_URL}/demo", ReceiptHandle="nope", VisibilityTimeout=0)
    assert err.value.response["Error"]["Code"] == "ReceiptHandleIsInvalid"


# --- delete ---


def test_delete_message(sqs):
    url = f"{QUEUE_URL}/demo"
    sqs.send_message(QueueUrl=url, MessageBody="bye")
    handle = sqs.receive_message(QueueUrl=url)["Messages"][0]["ReceiptHandle"]

    sqs.delete_message(QueueUrl=url, ReceiptHandle=handle)
    assert "Messages" not in sqs.receive_message(QueueUrl=url)

    # The (now stale) handle no longer matches any message.
    with pytest.raises(ClientError) as err:
        sqs.delete_message(QueueUrl=url, ReceiptHandle=handle)
    assert err.value.response["Error"]["Code"] == "ReceiptHandleIsInvalid"


def test_delete_message_invalid_handle(sqs):
    with pytest.raises(ClientError) as err:
        sqs.delete_message(QueueUrl=f"{QUEUE_URL}/demo", ReceiptHandle="ghost")
    assert err.value.response["Error"]["Code"] == "ReceiptHandleIsInvalid"


# --- dead-letter queue redrive ---


def _queue_with_redrive(sqs, max_receive_count: str) -> tuple[str, str]:
    dlq = sqs.create_queue(QueueName="poison")
    src = sqs.create_queue(
        QueueName="orders",
        Attributes={
            "VisibilityTimeout": "0.2",
            "RedrivePolicy": json.dumps(
                {"maxReceiveCount": max_receive_count, "deadLetterTargetArn": dlq["QueueUrl"]}
            ),
        },
    )
    return src["QueueUrl"], dlq["QueueUrl"]


def test_get_queue_attributes_redrive_policy(sqs):
    src, _ = _queue_with_redrive(sqs, "2")
    attrs = sqs.get_queue_attributes(QueueUrl=src, AttributeNames=["All"])["Attributes"]

    assert attrs["VisibilityTimeout"] == "0.2"
    policy = json.loads(attrs["RedrivePolicy"])
    assert policy["maxReceiveCount"] == "2"
    assert policy["deadLetterTargetArn"].endswith("/poison")
    assert attrs["QueueArn"].endswith(":orders")


def test_redrive_poison_message_to_dead_letter_queue(sqs):
    src, dlq = _queue_with_redrive(sqs, "2")
    sqs.send_message(QueueUrl=src, MessageBody="poisoned")

    # Two receives are delivered (maxReceiveCount = 2).
    first = sqs.receive_message(QueueUrl=src)
    assert len(first["Messages"]) == 1 and first["Messages"][0]["Attributes"]["ApproximateReceiveCount"] == "1"
    time.sleep(0.3)
    second = sqs.receive_message(QueueUrl=src)
    assert len(second["Messages"]) == 1 and second["Messages"][0]["Attributes"]["ApproximateReceiveCount"] == "2"

    # The next receive attempt moves the message to the DLQ instead.
    time.sleep(0.3)
    assert "Messages" not in sqs.receive_message(QueueUrl=src)

    moved = sqs.receive_message(QueueUrl=dlq)
    assert len(moved["Messages"]) == 1
    assert moved["Messages"][0]["Body"] == "poisoned"
    assert moved["Messages"][0]["Attributes"]["ApproximateReceiveCount"] == "2"


def test_redrive_policy_requires_existing_dead_letter_queue(sqs):
    with pytest.raises(ClientError) as err:
        sqs.create_queue(
            QueueName="orders",
            Attributes={
                "RedrivePolicy": json.dumps(
                    {"maxReceiveCount": "2", "deadLetterTargetArn": f"{QUEUE_URL}/ghost"}
                )
            },
        )
    assert err.value.response["Error"]["Code"] == "QueueDoesNotExist"
