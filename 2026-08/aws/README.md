# fs-s3

S3-compatible boto3 API over a local `data/` store: bucket and object
metadata live in `data/s3.parquet` (one row each), and object contents live
under `data/data/` (one flat file per object).
Stateless: every response (listings, hashes, metadata) is computed live
from the parquet index and the files it names per request — no cache, no
background indexing.

Implements the S3 subset boto3 needs to manage, store and retrieve
objects: `ListBuckets`, `CreateBucket`, `HeadBucket`, `DeleteBucket`,
`ListObjects` (v1 & v2, with `Prefix` / `Delimiter`, and paging via
`MaxKeys` / `Marker` / `StartAfter` / `ContinuationToken` - listings
report `IsTruncated` plus `NextMarker` / `NextContinuationToken`, and a
page's `MaxKeys` counts objects and common prefixes alike), `HeadObject`,
`GetObject`, `PutObject`, `CopyObject`, `DeleteObjects` (batch, `?delete=`),
`DeleteObject` and the multipart upload operations (`CreateMultipartUpload`,
`UploadPart`, `UploadPartCopy`, `ListParts`, `CompleteMultipartUpload`,
`AbortMultipartUpload`).
`GetObject` and
`HeadObject` honour the `Range` header: a satisfiable range returns 206 with a
`Content-Range` covering the requested span (`bytes=start-end`,
`bytes=start-`, `bytes=-suffix`); an unsatisfiable or malformed range
returns 416 `InvalidRange`. They also honour the `If-Match` /
`If-None-Match` conditional headers: a failed `If-Match` returns 412
`PreconditionFailed`, and a matched `If-None-Match` returns 304 Not
Modified. On `PutObject` the same headers guard the write: any failed
precondition aborts it with 412 `PreconditionFailed` (`If-None-Match: *`
is the usual create-only-if-absent guard). `CopyObject` (a `PutObject`
carrying the
`x-amz-copy-source` header, so `s3.copy_object`) copies the source
object's bytes to the destination and gives the new object a fresh
`LastModified`; a missing source key returns `NoSuchKey`. `DeleteObjects`
(`s3.delete_objects`) removes several keys in one request and reports each as
`Deleted` in the `DeleteResult` (deleting a missing key is a no-op, like
`DeleteObject`).
`Quiet` suppresses the result list. Signatures are accepted but not verified.

Multipart uploads (``s3.create_multipart_upload`` / ``upload_part`` /
``upload_part_copy`` / ``list_parts`` / ``complete_multipart_upload`` /
``abort_multipart_upload``)
store in-flight parts under ``data/uploads/<bucket>/<upload-id>/`` - outside
the index, so listings never see them.  Completing an upload assembles the
object like ``PutObject`` (with the S3-style ``md5-of-md5s-N`` ETag) and
drops the parts; aborting just removes them.  ``boto3``'s managed transfers
(``upload_file`` / ``upload_fileobj``) switch to this path automatically
above the 8 MiB threshold.

User-defined metadata (``x-amz-meta-*`` headers) is persisted per object in
the parquet index's JSON ``metadata`` column and returned by ``GetObject``,
``HeadObject`` and ``CopyObject``.  ``CopyObject`` honours the
``x-amz-metadata-directive`` header: ``COPY`` (the default) keeps the source
object's metadata, ``REPLACE`` uses the request's own headers - so a
``REPLACE`` without metadata clears it.  A multipart upload takes its
metadata from the ``CreateMultipartUpload`` request, like S3.

Buckets and objects are rows in the parquet index: `CreateBucket` adds a
bucket row,
`PutObject` writes the object's bytes under `data/data/<bucket>/` (a flat
percent-encoded file per key, so a key can never escape the store or
collide with a directory) and adds its metadata row, `DeleteObject`
removes both, and `DeleteBucket` removes the bucket row and its content
directory, so buckets are isolated and everything reflects the live
store. Listings are computed from the index, without walking the
filesystem.
`DeleteBucket` only succeeds while the bucket holds no objects — it
returns `BucketNotEmpty` (409) if any remain. Deleting a missing bucket
returns `NoSuchBucket`.
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

    .venv/bin/python -m pytest tests/test_s3.py tests/test_multipart.py

The suite boots a private server per test against an isolated temporary
store (the store instance is swapped via ``monkeypatch``); it never
touches ``data/``.

# fs-sqs

A minimal SQS-compatible boto3 API over in-process queues
(``aws/api/sqs_api.py``, wired into ``main.py`` alongside the S3 API).
Implemented operations: ``SendMessage``, ``ReceiveMessage``,
``DeleteMessage``, ``ChangeMessageVisibility``, ``CreateQueue``,
``DeleteQueue`` and ``GetQueueAttributes``. Queues live in the module-level
``QUEUES`` dict (name -> queue); messages are in-memory only and are lost
on restart. Calls are accepted exactly as boto3 sends them and errors like
``QueueDoesNotExist`` are surfaced as ``ClientError``.

**Visibility timeout.** A received message is hidden from other receivers
for its visibility timeout (default 30s). The timeout is set per queue
(``VisibilityTimeout`` attribute on ``CreateQueue``), per receive (the
``VisibilityTimeout`` parameter of ``ReceiveMessage``) and can be adjusted
on the fly with ``ChangeMessageVisibility`` (pass 0 to make the message
visible immediately). If the message is not deleted before the timeout
lapses it is redelivered with a fresh ``ReceiptHandle`` and an incremented
``ApproximateReceiveCount``; a message deleted via ``DeleteMessage`` is gone.

**Dead-letter queue.** ``CreateQueue`` accepts a ``RedrivePolicy`` attribute
(``{"maxReceiveCount": N, "deadLetterTargetArn": <queue URL or ARN>}``; the
target must exist and must not be the queue itself). A message that has
already been received ``maxReceiveCount`` times is moved to the
dead-letter queue on its next receive instead of being delivered again.
The policy is reported back by ``GetQueueAttributes``.

## Run

    .venv/bin/uvicorn main:app --port 8000

Served through the same ``main.py`` entrypoint as S3; requests carrying an
``x-amz-target`` header (e.g. ``AmazonSQS.SendMessage``) are routed here.

## Use

```python
import boto3
import json

sqs = boto3.client(
    "sqs",
    endpoint_url="http://127.0.0.1:8000",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)
demo = sqs.create_queue(QueueName="demo")
sqs.send_message(QueueUrl=demo["QueueUrl"], MessageBody="hi")
message = sqs.receive_message(QueueUrl=demo["QueueUrl"])["Messages"][0]
sqs.delete_message(QueueUrl=demo["QueueUrl"], ReceiptHandle=message["ReceiptHandle"])

# with a dead-letter queue:
poison = sqs.create_queue(QueueName="demo-poison")
orders = sqs.create_queue(
    QueueName="orders",
    Attributes={
        "VisibilityTimeout": "5",
        "RedrivePolicy": json.dumps(
            {"maxReceiveCount": "3", "deadLetterTargetArn": poison["QueueUrl"]}
        ),
    },
)
```

## Test

    .venv/bin/python -m pytest tests/test_sqs.py

Each test boots a private server per test against an isolated queue set
(``QUEUES`` is replaced via ``monkeypatch``); runs never share state.  The
suite covers the visibility-timeout lifecycle (receive, redelivery,
visibility change, delete) and redrive to a dead-letter queue.
