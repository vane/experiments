"""Pytest suite driving the API with a real boto3 client over HTTP.

Each test runs against a fresh server started in-process (uvicorn in a
background thread) with the store mocked to an isolated temporary
directory, so tests are hermetic and never touch the checked-in
``data/`` directory.

Run from the project root::

    pytest tests/test_s3.py
"""

import hashlib
import socket
import threading
import time
import urllib.request
from pathlib import Path

import boto3
import pytest
import uvicorn
from botocore.config import Config
from botocore.exceptions import ClientError

import aws.api.s3_api as s3_api
import aws.routes.s3 as s3_routes


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
def s3(tmp_path, monkeypatch):
    # Mock the on-disk store to the test's private directory and seed the
    # same bucket layout the API exposes (bucket "data" -> ./data/*).
    monkeypatch.setattr(s3_routes, "DATA_DIR", tmp_path)
    bucket = tmp_path / "data"
    notes = bucket / "notes"
    notes.mkdir(parents=True)
    (bucket / "hello.txt").write_bytes(b"hello from fs-s3\n")
    (notes / "a.md").write_bytes(b"# note a\n\ns3 test\n")
    (notes / "b.txt").write_bytes(b"b\n")

    port = _free_port()
    config = uvicorn.Config(
        s3_api.app, host="127.0.0.1", port=port,
        log_level="warning", access_log=False, lifespan="off",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_ready(port)

    client = boto3.client(
        "s3",
        endpoint_url=f"http://127.0.0.1:{port}",
        aws_access_key_id="test",
        aws_secret_access_key="test",  # accepted but not verified
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}),
    )
    try:
        yield client
    finally:
        server.should_exit = True
        thread.join(timeout=10)


# --- bucket level ---


def test_list_and_head_buckets(s3):
    assert "data" in {b["Name"] for b in s3.list_buckets()["Buckets"]}
    s3.head_bucket(Bucket="data")


def test_create_bucket_and_isolation(s3):
    assert "_bkt" in s3.create_bucket(Bucket="_bkt").get("Location", "")
    assert "_bkt" in {b["Name"] for b in s3.list_buckets()["Buckets"]}
    s3.head_bucket(Bucket="_bkt")

    s3.put_object(Bucket="_bkt", Key="x/y.txt", Body=b"bucket-scoped\n")
    assert {c["Key"] for c in s3.list_objects_v2(Bucket="_bkt")["Contents"]} == {"x/y.txt"}
    assert "x/y.txt" not in {c["Key"] for c in s3.list_objects_v2(Bucket="data")["Contents"]}


def test_missing_bucket_errors(s3):
    with pytest.raises(ClientError) as err:
        s3.list_objects_v2(Bucket="_missing")
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"

    with pytest.raises(ClientError) as err:
        s3.delete_object(Bucket="_missing", Key="x")
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"


# --- listing ---


def test_list_objects_v2(s3):
    all_keys = {c["Key"] for c in s3.list_objects_v2(Bucket="data")["Contents"]}
    assert {"hello.txt", "notes/a.md", "notes/b.txt"} <= all_keys

    prefixed = s3.list_objects_v2(Bucket="data", Prefix="notes/")
    assert {c["Key"] for c in prefixed["Contents"]} == {"notes/a.md", "notes/b.txt"}

    delim = s3.list_objects_v2(Bucket="data", Delimiter="/")
    assert "hello.txt" in {c["Key"] for c in delim["Contents"]}
    assert "notes/" in {cp["Prefix"] for cp in delim.get("CommonPrefixes", [])}


def test_list_objects_v1(s3):
    assert any(c["Key"] == "hello.txt" for c in s3.list_objects(Bucket="data")["Contents"])


# --- object retrieval ---


def test_head_and_get_object(s3):
    head = s3.head_object(Bucket="data", Key="hello.txt")
    assert head["ContentLength"] == 17 and head["ETag"]

    assert s3.get_object(Bucket="data", Key="hello.txt")["Body"].read() == b"hello from fs-s3\n"
    assert s3.get_object(Bucket="data", Key="notes/a.md")["Body"].read() == b"# note a\n\ns3 test\n"


def test_missing_key_no_such_key(s3):
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="data", Key="nope.txt")
    assert err.value.response["Error"]["Code"] == "NoSuchKey"


def test_key_traversal_is_contained(s3):
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="data", Key="../s3_api.py")
    assert err.value.response["Error"]["Code"] == "NoSuchKey"


# --- range requests ---


def test_get_object_range(s3):
    body = b"hello from fs-s3\n"

    part = s3.get_object(Bucket="data", Key="hello.txt", Range="bytes=0-4")
    assert part["Body"].read() == b"hello"
    assert part["ContentRange"] == "bytes 0-4/17"
    assert part["ContentLength"] == 5
    assert part["ETag"]
    assert part["ResponseMetadata"]["HTTPStatusCode"] == 206

    # an open-ended range runs to the end of the object
    part = s3.get_object(Bucket="data", Key="hello.txt", Range="bytes=12-")
    assert part["Body"].read() == body[12:]
    assert part["ContentRange"] == "bytes 12-16/17"

    # a suffix range takes the last N bytes
    part = s3.get_object(Bucket="data", Key="hello.txt", Range="bytes=-5")
    assert part["Body"].read() == body[-5:]
    assert part["ContentRange"] == "bytes 12-16/17"

    # a suffix longer than the object returns the whole object
    part = s3.get_object(Bucket="data", Key="hello.txt", Range="bytes=-999")
    assert part["Body"].read() == body
    assert part["ContentRange"] == "bytes 0-16/17"


def test_get_object_range_unsatisfiable(s3):
    for rng in ("bytes=17-", "bytes=99-100", "bytes=5-2"):
        with pytest.raises(ClientError) as err:
            s3.get_object(Bucket="data", Key="hello.txt", Range=rng)
        assert err.value.response["Error"]["Code"] == "InvalidRange"
        assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 416


def test_head_object_range(s3):
    head = s3.head_object(Bucket="data", Key="hello.txt", Range="bytes=0-4")
    assert head["ResponseMetadata"]["HTTPStatusCode"] == 206
    assert head["ContentRange"] == "bytes 0-4/17"
    assert head["ContentLength"] == 5

    # without a range the head still reports the full object
    full = s3.head_object(Bucket="data", Key="hello.txt")
    assert "ContentRange" not in full
    assert full["ContentLength"] == 17


def test_head_object_range_unsatisfiable(s3):
    with pytest.raises(ClientError) as err:
        s3.head_object(Bucket="data", Key="hello.txt", Range="bytes=99-")
    meta = err.value.response["ResponseMetadata"]
    assert meta["HTTPStatusCode"] == 416
    assert meta["HTTPHeaders"]["content-range"] == "bytes */17"


# --- put ---


def test_put_object_roundtrip(s3):
    sent = b"fresh upload bytes\n"
    put = s3.put_object(Bucket="data", Key="_put/new.txt", Body=sent)
    assert put["ETag"] == f'"{hashlib.md5(sent).hexdigest()}"'
    assert s3.get_object(Bucket="data", Key="_put/new.txt")["Body"].read() == sent
    assert s3.head_object(Bucket="data", Key="_put/new.txt")["ContentLength"] == len(sent)
    assert "_put/new.txt" in {c["Key"] for c in s3.list_objects_v2(Bucket="data", Prefix="_put/")["Contents"]}


def test_put_creates_intermediate_dirs(s3):
    s3.put_object(Bucket="data", Key="_put/a/b/c.txt", Body=b"nested\n")
    assert s3.get_object(Bucket="data", Key="_put/a/b/c.txt")["Body"].read() == b"nested\n"


def test_put_overwrites(s3):
    s3.put_object(Bucket="data", Key="_put/new.txt", Body=b"v1\n")
    s3.put_object(Bucket="data", Key="_put/new.txt", Body=b"v2\n")
    assert s3.get_object(Bucket="data", Key="_put/new.txt")["Body"].read() == b"v2\n"


def test_put_large_body(s3):
    big = bytes(range(256)) * 4096  # 1 MiB
    s3.put_object(Bucket="data", Key="_put/big.bin", Body=big)
    assert s3.get_object(Bucket="data", Key="_put/big.bin")["Body"].read() == big


# --- delete ---


def test_delete_object_and_idempotency(s3):
    s3.put_object(Bucket="data", Key="_put/del.txt", Body=b"bye\n")
    assert s3.delete_object(Bucket="data", Key="_put/del.txt")["ResponseMetadata"]["HTTPStatusCode"] == 204

    for op in (s3.get_object, s3.head_object):
        with pytest.raises(ClientError) as err:
            op(Bucket="data", Key="_put/del.txt")
        assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert "_put/del.txt" not in {
        c["Key"] for c in s3.list_objects_v2(Bucket="data", Prefix="_put/").get("Contents", [])
    }

    # delete is idempotent, like S3
    assert s3.delete_object(Bucket="data", Key="_put/del.txt")["ResponseMetadata"]["HTTPStatusCode"] == 204


# --- delete bucket ---


def test_delete_bucket(s3):
    s3.create_bucket(Bucket="_delbkt")
    assert s3.delete_bucket(Bucket="_delbkt")["ResponseMetadata"]["HTTPStatusCode"] == 204

    with pytest.raises(ClientError) as err:
        s3.head_bucket(Bucket="_delbkt")
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert "_delbkt" not in {b["Name"] for b in s3.list_buckets()["Buckets"]}

    with pytest.raises(ClientError) as err:
        s3.delete_bucket(Bucket="_delbkt")
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"


def test_delete_bucket_not_empty(s3):
    s3.create_bucket(Bucket="_full")
    s3.put_object(Bucket="_full", Key="x/y.txt", Body=b"keep\n")

    with pytest.raises(ClientError) as err:
        s3.delete_bucket(Bucket="_full")
    assert err.value.response["Error"]["Code"] == "BucketNotEmpty"

    # removing the object leaves only an empty directory -> bucket is now deletable
    s3.delete_object(Bucket="_full", Key="x/y.txt")
    assert s3.delete_bucket(Bucket="_full")["ResponseMetadata"]["HTTPStatusCode"] == 204


def test_delete_bucket_missing(s3):
    with pytest.raises(ClientError) as err:
        s3.delete_bucket(Bucket="_missing")
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"
