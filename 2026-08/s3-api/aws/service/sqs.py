import hashlib
import queue
import re
import uuid
from urllib.parse import urlsplit

from fastapi.responses import JSONResponse, Response

# Queue name -> in-memory FIFO queue.  Every request reads/writes this dict;
# tests replace it (monkeypatch) to keep each run hermetic.
QUEUES: dict[str, queue.Queue[str]] = {}
# Queue name -> last sequence number handed out, to build SequenceNumber.
_SEQUENCES: dict[str, int] = {}


def error_response(code: str, message: str) -> JSONResponse:
    """AWS JSON 1.0 error envelope; botocore maps ``__type`` to ``Error.Code``."""
    return JSONResponse(
        {"__type": code, "message": message},
        status_code=400,
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

    # The queue name is the last path segment of the queue URL.
    name = queue_name(queue_url)
    target_queue = QUEUES.get(name)
    if target_queue is None:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")

    sequence = _SEQUENCES.get(name, 0) + 1
    _SEQUENCES[name] = sequence
    target_queue.put(message_body)

    return JSONResponse(
        {
            "MessageId": str(uuid.uuid4()),
            "MD5OfMessageBody": hashlib.md5(message_body.encode("utf-8")).hexdigest(),
            "SequenceNumber": str(sequence),
        },
        media_type="application/x-amz-json-1.0",
    )


def create_queue(payload: dict, base_url: str) -> JSONResponse:
    """AmazonSQS.CreateQueue: create a new empty queue."""
    name = payload.get("QueueName")
    if not isinstance(name, str) or name == "":
        return error_response("MissingParameter", "The request must contain the QueueName parameter.")
    # A queue name is up to 80 chars: alphanumerics, hyphens, underscores;
    # a FIFO queue additionally ends with ".fifo".
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,75}(\.fifo)?", name):
        return error_response("InvalidParameterValue", "QueueName must be 1-80 characters of alphanumerics, hyphens and underscores.")
    if name in QUEUES:
        return error_response("QueueNameExists", f"A queue named {name} already exists.")

    QUEUES[name] = queue.Queue()
    _SEQUENCES[name] = 0
    return JSONResponse(
        {"QueueUrl": f"{base_url}/{name}"},
        media_type="application/x-amz-json-1.0",
    )


def queue_name(queue_url: str) -> str:
    """The queue name is the last path segment of the queue URL."""
    return urlsplit(queue_url).path.rstrip("/").rsplit("/", 1)[-1]


def delete_queue(payload: dict) -> JSONResponse:
    """AmazonSQS.DeleteQueue: delete a queue and drop its messages."""
    queue_url = payload.get("QueueUrl") or ""
    if not queue_url:
        return error_response("MissingParameter", "The request must contain the QueueUrl parameter.")
    name = queue_name(queue_url)
    if name not in QUEUES:
        return error_response("QueueDoesNotExist", "The specified queue does not exist.")
    del QUEUES[name]
    _SEQUENCES.pop(name, None)
    return Response(status_code=200)
