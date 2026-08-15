# fs-s3

S3-compatible boto3 API over a local `data/` directory.
Stateless: every response (listings, hashes, metadata) is computed live
from the filesystem per request — no cache, no background indexing.

Implements the S3 subset boto3 needs to manage, store and retrieve
objects: `ListBuckets`, `CreateBucket`, `HeadBucket`, `DeleteBucket`,
`ListObjects` (v1 & v2, with `Prefix` / `Delimiter`), `HeadObject`,
`GetObject`, `PutObject`, `DeleteObject`. Signatures are accepted but
not verified.

Buckets are real: each bucket is a directory under `data/`, and object
keys map to files inside that bucket's directory. `CreateBucket` makes
the directory, `PutObject` writes files directly into it (creating
intermediate directories as needed), `DeleteObject` removes files, and
`DeleteBucket` removes the directory, so buckets are isolated and
everything reflects the live filesystem.
`DeleteBucket` only succeeds while the bucket holds no objects — it
returns `BucketNotEmpty` (409) if any files remain. Empty directories
under the bucket are not objects, so they don't block deletion.
Deleting a missing bucket returns `NoSuchBucket`.
Missing buckets return `NoSuchBucket`, missing keys `NoSuchKey`.

## Run

    python -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/uvicorn main:app --port 8000

The API is a single FastAPI app (``main.py``) that dispatches each request by
its ``x-amz-target`` header: SQS calls (which carry a target) go to
``aws/api/sqs_api``, everything else is treated as path-based S3
(``aws/api/s3_api``).

## Use

```python
import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    endpoint_url="http://127.0.0.1:8000",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    config=Config(s3={"addressing_style": "path"}),
)
s3.create_bucket(Bucket="demo")
s3.put_object(Bucket="demo", Key="hello.txt", Body=b"hi")
data = s3.get_object(Bucket="demo", Key="hello.txt")["Body"].read()
```

## Test

    .venv/bin/python -m pytest tests/test_s3.py

The suite boots a private server per test against an isolated temporary
store (the app's data directory is mocked via ``monkeypatch``); it never
touches ``data/``.

# fs-sqs

A minimal SQS-compatible boto3 API over in-process queues
(``aws/api/sqs_api.py``, wired into ``main.py`` alongside the S3 API). Only
``SendMessage`` is implemented: given a ``MessageBody`` and ``QueueUrl`` it
puts the body onto a named in-process ``queue.Queue``. Queues live in the
module-level ``QUEUES`` dict (name -> queue); messages are in-memory only and
are lost on restart. ``SendMessage`` is compatible with the boto3 SQS client
— messages are accepted exactly as boto3 sends them and errors like
``QueueDoesNotExist`` are surfaced as ``ClientError``.

## Run

    .venv/bin/uvicorn main:app --port 8000

Served through the same ``main.py`` entrypoint as S3; requests carrying an
``x-amz-target`` header (e.g. ``AmazonSQS.SendMessage``) are routed here.

## Use

```python
import boto3

sqs = boto3.client(
    "sqs",
    endpoint_url="http://127.0.0.1:8000",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)
sqs.send_message(QueueUrl="https://sqs.us-east-1.amazonaws.com/123456789012/demo", MessageBody="hi")
```

## Test

    .venv/bin/python -m pytest tests/test_sqs.py

Each test boots a private server per test against an isolated queue set
(``QUEUES`` is replaced via ``monkeypatch``); runs never share state.
