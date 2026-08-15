"""In-process SQS store and operations with boto3-compatible semantics.

Queues live in the module-level ``QUEUES`` dict (name -> :class:`Queue`),
backed by in-memory FIFO queues.  Two SQS behaviours are modelled on top:

* **Visibility timeout** - a message that has been received is hidden from
  other receivers until its timeout lapses (default 30s, configurable per
  queue via the ``VisibilityTimeout`` attribute, per receive via the
  ``VisibilityTimeout`` parameter, and on the fly with
  ``ChangeMessageVisibility``).  When the timeout lapses the message is
  redelivered with a fresh receipt handle and an incremented receive count.
* **Dead-letter queue** - a queue may carry a ``RedrivePolicy`` (a
  ``maxReceiveCount`` plus ``deadLetterTargetArn``).  A message that has
  already been received ``maxReceiveCount`` times is moved to the target
  queue on its next receive instead of being delivered.

Everything is in-memory; queues and messages are lost on restart.  Tests
replace ``QUEUES`` (monkeypatch) to keep each run hermetic.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
import uuid
from collections import deque
from urllib.parse import urlsplit

from fastapi.responses import JSONResponse, Response

# Default visibility timeout, in seconds (matches SQS).
DEFAULT_VISIBILITY_TIMEOUT = 30.0

# Queue name -> queue.  Every request reads/writes this dict; tests replace
# it (monkeypatch) to keep each run hermetic.
QUEUES: dict[str, Queue] = {}


class Message:
    """One queue message.

    ``visible_at`` is a monotonic-clock deadline: while the clock is below
    it the message is in flight (hidden from receivers).
    """

    def __init__(self, body: str) -> None:
        self.body = body
        self.message_id = str(uuid.uuid4())
        self.receipt_handle = ""  # set on receive; invalidated by redelivery
        self.receive_count = 0
        self.visible_at = 0.0


class Queue:
    """A named in-memory queue with visibility-timeout and redrive settings."""

    def __init__(self, name: str, visibility_timeout: float = DEFAULT_VISIBILITY_TIMEOUT) -> None:
        self.name = name
        self.visibility_timeout = visibility_timeout
        self.messages: deque[Message] = deque()
        # None or {"max_receive_count": int, "target": str, "target_ref": str}.
        self.redrive_policy: dict | None = None
        self._sequence = 0


def error_response(code: str, message: str) -> JSONResponse:
    """AWS JSON 1.0 error envelope; botocore maps ``__type`` to ``Error.Code``."""
    return JSONResponse(
        {"__type": code, "message": message},
        status_code=400,
        media_type="application/x-amz-json-1.0",
    )


def queue_name(queue_url: str) -> str:
    """The queue name is the last path segment of the queue URL."""
    return urlsplit(queue_url).path.rstrip("/").rsplit("/", 1)[-1]


def resolve_queue_ref(ref: str) -> str:
    """Resolve a queue reference (a URL or an ARN) to a queue name."""
    if "://" in ref:
        return urlsplit(ref).path.rstrip("/").rsplit("/", 1)[-1]
    # ARN form: arn:aws:sqs:<region>:<account>:<queue-name>
    return ref.rsplit(":", 1)[-1]


def create_queue(payload: dict, base_url: str) -> JSONResponse:
    """AmazonSQS.CreateQueue: create a new empty queue.

    Honours the ``VisibilityTimeout`` and ``RedrivePolicy`` (dead-letter
    queue) attributes.
    """
    name = payload.get("QueueName")
    if not isinstance(name, str) or name == "":
        return error_response("MissingParameter", "The request must contain the QueueName parameter.")
    # A queue name is up to 80 chars: alphanumerics, hyphens, underscores;
    # a FIFO queue additionally ends with ".fifo".
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,75}(\.fifo)?", name):
        return error_response("InvalidParameterValue", "QueueName must be 1-80 characters of alphanumerics, hyphens and underscores.")
    if name in QUEUES:
        return error_response("QueueNameExists", f"A queue named {name} already exists.")

    queue = Queue(name)
    attributes = payload.get("Attributes") or {}
    if "VisibilityTimeout" in attributes:
        try:
            queue.visibility_timeout = float(attributes["VisibilityTimeout"])
        except (TypeError, ValueError):
            return error_response("InvalidAttributeValue", "VisibilityTimeout must be a number of seconds.")
        if not 0 <= queue.visibility_timeout <= 43200:
            return error_response("InvalidAttributeValue", "VisibilityTimeout must be between 0 and 43200 seconds.")
    if "RedrivePolicy" in attributes:
        try:
            policy = json.loads(attributes["RedrivePolicy"])
            max_receive_count = int(policy["maxReceiveCount"])
            target_ref = str(policy["deadLetterTargetArn"])
        except (ValueError, KeyError, TypeError):
            return error_response("InvalidRedrivePolicy", "RedrivePolicy must contain a numeric maxReceiveCount and a deadLetterTargetArn.")
        if not 1 <= max_receive_count <= 10000:
            return error_response("InvalidRedrivePolicy", "maxReceiveCount must be between 1 and 10000.")
        target = resolve_queue_ref(target_ref)
        if target == name:
            return error_response("InvalidRedrivePolicy", "The dead-letter queue cannot be the queue itself.")
        if target not in QUEUES:
            return error_response("QueueDoesNotExist", f"The dead-letter queue {target_ref} does not exist.")
        queue.redrive_policy = {"max_receive_count": max_receive_count, "target": target, "target_ref": target_ref}

    QUEUES[name] = queue
    return JSONResponse(
        {"QueueUrl": f"{base_url}/{name}"},
        media_type="application/x-amz-json-1.0",
    )


def send_message(payload: dict) -> JSONResponse:
    """AmazonSQS.SendMessage: put a message body onto a named queue."""
    queue_url = payload.get("QueueUrl") or ""
    message_body = payload.get("MessageBody")
    if not queue_url:
        return error_response("MissingParameter", "The request must contain the QueueUrl parameter.")
    if message_body is None:
        return error_response("MissingParameter", "The request must contain the MessageBody parameter.")
    if not isinstance(message_body, str) or message_body == "":
        return error_response("InvalidParameterValue", "MessageBody must be a non-empty string.")

    target_queue = QUEUES.get(queue_name(queue_url))
    if target_queue is None:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")

    message = Message(message_body)
    target_queue._sequence += 1
    target_queue.messages.append(message)
    return JSONResponse(
        {
            "MessageId": message.message_id,
            "MD5OfMessageBody": hashlib.md5(message_body.encode("utf-8")).hexdigest(),
            "SequenceNumber": str(target_queue._sequence),
        },
        media_type="application/x-amz-json-1.0",
    )


def _in_flight(queue: Queue) -> int:
    now = time.monotonic()
    return sum(1 for m in queue.messages if m.visible_at > now)


def _take_deliverable(queue: Queue, max_messages: int, visibility: float) -> list[Message]:
    """Hand out up to ``max_messages`` visible messages, hiding them for
    ``visibility`` seconds.

    A message that has already been received ``maxReceiveCount`` times under
    an active redrive policy is moved to the dead-letter queue instead of
    being delivered.
    """
    now = time.monotonic()
    batch: list[Message] = []
    for message in list(queue.messages):
        if len(batch) >= max_messages:
            break
        if message.visible_at > now:
            continue
        if queue.redrive_policy and message.receive_count >= queue.redrive_policy["max_receive_count"]:
            _redrive(queue, message)
            continue
        message.receive_count += 1
        message.receipt_handle = str(uuid.uuid4())
        message.visible_at = now + visibility
        batch.append(message)
    return batch


def _redrive(queue: Queue, message: Message) -> None:
    """Move a poison message to the queue's dead-letter queue.

    The moved message keeps the source queue's receive history: the first
    delivery in the DLQ reports the source queue's final count, and each
    further DLQ delivery increments from there.
    """
    target = QUEUES.get(queue.redrive_policy["target"])
    queue.messages.remove(message)
    if target is None:  # the dead-letter queue was deleted; drop the message
        return
    moved = Message(message.body)
    # Deliveries bump the count before reporting, so shift by one: the first
    # DLQ delivery then reports the source queue's count.
    moved.receive_count = max(message.receive_count - 1, 0)
    target.messages.append(moved)


async def receive_message(payload: dict) -> JSONResponse:
    """AmazonSQS.ReceiveMessage: take up to ``MaxNumberOfMessages`` visible
    messages (long-polling up to ``WaitTimeSeconds``), hiding them for their
    visibility timeout (``VisibilityTimeout`` overrides the queue default).
    """
    queue_url = payload.get("QueueUrl") or ""
    if not queue_url:
        return error_response("MissingParameter", "The request must contain the QueueUrl parameter.")
    queue = QUEUES.get(queue_name(queue_url))
    if queue is None:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")

    try:
        max_messages = int(payload.get("MaxNumberOfMessages", 1))
        wait_seconds = float(payload.get("WaitTimeSeconds", 0) or 0)
    except (TypeError, ValueError):
        return error_response("InvalidParameterValue", "MaxNumberOfMessages and WaitTimeSeconds must be numbers.")
    if not 1 <= max_messages <= 10:
        return error_response("InvalidParameterValue", "MaxNumberOfMessages must be between 1 and 10.")
    if not 0 <= wait_seconds <= 20:
        return error_response("InvalidParameterValue", "WaitTimeSeconds must be between 0 and 20.")

    visibility = queue.visibility_timeout
    if "VisibilityTimeout" in payload:
        try:
            visibility = float(payload["VisibilityTimeout"])
        except (TypeError, ValueError):
            return error_response("InvalidParameterValue", "VisibilityTimeout must be a number of seconds.")
        if not 0 <= visibility <= 43200:
            return error_response("InvalidParameterValue", "VisibilityTimeout must be between 0 and 43200 seconds.")

    deadline = time.monotonic() + wait_seconds
    while True:
        batch = _take_deliverable(queue, max_messages, visibility)
        if batch or time.monotonic() >= deadline:
            break
        await asyncio.sleep(0.05)

    result: dict = {"ApproximateNumberOfMessagesInFlight": _in_flight(queue)}
    if batch:
        result["Messages"] = [
            {
                "MessageId": m.message_id,
                "ReceiptHandle": m.receipt_handle,
                "MD5OfMessageBody": hashlib.md5(m.body.encode("utf-8")).hexdigest(),
                "Body": m.body,
                "Attributes": {"ApproximateReceiveCount": str(m.receive_count)},
            }
            for m in batch
        ]
    return JSONResponse(result, media_type="application/x-amz-json-1.0")


def delete_message(payload: dict) -> JSONResponse:
    """AmazonSQS.DeleteMessage: permanently remove a received message."""
    queue_url = payload.get("QueueUrl") or ""
    if not queue_url:
        return error_response("MissingParameter", "The request must contain the QueueUrl parameter.")
    handle = payload.get("ReceiptHandle") or ""
    queue = QUEUES.get(queue_name(queue_url))
    if queue is None:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")
    for message in list(queue.messages):
        if message.receipt_handle == handle:
            queue.messages.remove(message)
            return Response(status_code=200)
    return error_response("ReceiptHandleIsInvalid", "The specified receipt handle does not match any message on the queue.")


def change_message_visibility(payload: dict) -> JSONResponse:
    """AmazonSQS.ChangeMessageVisibility: extend (or cancel, with 0) a
    message's visibility timeout."""
    queue_url = payload.get("QueueUrl") or ""
    if not queue_url:
        return error_response("MissingParameter", "The request must contain the QueueUrl parameter.")
    handle = payload.get("ReceiptHandle") or ""
    queue = QUEUES.get(queue_name(queue_url))
    if queue is None:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")
    try:
        visibility = float(payload.get("VisibilityTimeout", queue.visibility_timeout))
    except (TypeError, ValueError):
        return error_response("InvalidAttributeValue", "VisibilityTimeout must be a number of seconds.")
    if not 0 <= visibility <= 43200:
        return error_response("InvalidAttributeValue", "VisibilityTimeout must be between 0 and 43200 seconds.")
    for message in queue.messages:
        if message.receipt_handle == handle:
            message.visible_at = time.monotonic() + visibility
            return Response(status_code=200)
    return error_response("ReceiptHandleIsInvalid", "The specified receipt handle does not match any message on the queue.")


def get_queue_attributes(payload: dict) -> JSONResponse:
    """AmazonSQS.GetQueueAttributes: report a queue's settings."""
    queue_url = payload.get("QueueUrl") or ""
    if not queue_url:
        return error_response("MissingParameter", "The request must contain the QueueUrl parameter.")
    queue = QUEUES.get(queue_name(queue_url))
    if queue is None:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")

    requested = payload.get("AttributeNames") or []
    if not requested or "All" in requested:
        requested = ["QueueArn", "VisibilityTimeout", "RedrivePolicy", "MaximumMessageSize"]
    attributes: dict[str, str] = {}
    if "QueueArn" in requested:
        attributes["QueueArn"] = f"arn:aws:sqs:us-east-1:123456789012:{queue.name}"
    if "VisibilityTimeout" in requested:
        attributes["VisibilityTimeout"] = f"{queue.visibility_timeout:g}"
    if "RedrivePolicy" in requested and queue.redrive_policy is not None:
        attributes["RedrivePolicy"] = json.dumps(
            {
                "maxReceiveCount": str(queue.redrive_policy["max_receive_count"]),
                "deadLetterTargetArn": queue.redrive_policy["target_ref"],
            }
        )
    if "MaximumMessageSize" in requested:
        attributes["MaximumMessageSize"] = "262144"
    return JSONResponse({"Attributes": attributes}, media_type="application/x-amz-json-1.0")


def delete_queue(payload: dict) -> JSONResponse:
    """AmazonSQS.DeleteQueue: delete a queue and drop its messages."""
    queue_url = payload.get("QueueUrl") or ""
    if not queue_url:
        return error_response("MissingParameter", "The request must contain the QueueUrl parameter.")
    name = queue_name(queue_url)
    if name not in QUEUES:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")
    del QUEUES[name]
    return Response(status_code=200)
 