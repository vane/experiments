"""Pytest suite driving the API with a real boto3 client over HTTP.

Each test runs against a fresh server started in-process (uvicorn in a
background thread) with the store mocked to an isolated temporary
directory, so tests are hermetic and never touch the checked-in
``data/`` directory.

Run from the project root::

    pytest tests/test_s3.py
"""

import csv
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
from aws.service.s3 import S3Store


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
    # Point the store at the test's private directory and seed the same
    # bucket layout the API exposes (bucket "data": hello.txt, notes/*).
    backing = S3Store(tmp_path)
    backing.create_bucket("data")
    backing.put_object("data", "hello.txt", b"hello from fs-s3\n")
    backing.put_object("data", "notes/a.md", b"# note a\n\ns3 test\n")
    backing.put_object("data", "notes/b.txt", b"b\n")
    monkeypatch.setattr(s3_routes, "store", backing)

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


def test_key_traversal_is_contained(s3, tmp_path):
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="data", Key="../s3_api.py")
    assert err.value.response["Error"]["Code"] == "NoSuchKey"

    # traversal-y keys round-trip as ordinary objects, stored as flat
    # percent-encoded content files that can never reach outside the store
    s3.put_object(Bucket="data", Key="../s3_api.py", Body=b"contained\n")
    assert s3.get_object(Bucket="data", Key="../s3_api.py")["Body"].read() == b"contained\n"
    assert (tmp_path / "data" / "data" / "..%2Fs3_api.py").is_file()


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


def test_put_nested_key(s3):
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


# --- copy ---


def test_copy_object_roundtrip(s3):
    body = b"hello from fs-s3\n"
    resp = s3.copy_object(
        Bucket="data",
        CopySource={"Bucket": "data", "Key": "hello.txt"},
        Key="_copy/hello.txt",
    )
    assert resp["CopyObjectResult"]["ETag"] == f'"{hashlib.md5(body).hexdigest()}"'
    assert s3.get_object(Bucket="data", Key="_copy/hello.txt")["Body"].read() == body
    # the source object is untouched
    assert s3.get_object(Bucket="data", Key="hello.txt")["Body"].read() == body
    assert "_copy/hello.txt" in {
        c["Key"] for c in s3.list_objects_v2(Bucket="data", Prefix="_copy/")["Contents"]
    }


def test_copy_object_across_buckets(s3):
    s3.create_bucket(Bucket="_copybkt")
    s3.copy_object(
        Bucket="_copybkt",
        CopySource={"Bucket": "data", "Key": "notes/a.md"},
        Key="copied/a.md",
    )
    assert s3.get_object(Bucket="_copybkt", Key="copied/a.md")["Body"].read() == b"# note a\n\ns3 test\n"
    assert "copied/a.md" in {
        c["Key"] for c in s3.list_objects_v2(Bucket="_copybkt")["Contents"]
    }


def test_copy_object_nested_key(s3):
    s3.copy_object(
        Bucket="data",
        CopySource={"Bucket": "data", "Key": "hello.txt"},
        Key="_copy/a/b/c.txt",
    )
    assert s3.get_object(Bucket="data", Key="_copy/a/b/c.txt")["Body"].read() == b"hello from fs-s3\n"


def test_copy_object_self_is_idempotent(s3):
    resp = s3.copy_object(
        Bucket="data",
        CopySource={"Bucket": "data", "Key": "hello.txt"},
        Key="hello.txt",
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert s3.get_object(Bucket="data", Key="hello.txt")["Body"].read() == b"hello from fs-s3\n"


def test_copy_object_special_char_key(s3):
    s3.put_object(Bucket="data", Key="_copy/sp ace.txt", Body=b"space\n")
    s3.copy_object(
        Bucket="data",
        CopySource={"Bucket": "data", "Key": "_copy/sp ace.txt"},
        Key="_copy/sp ace 2.txt",
    )
    assert s3.get_object(Bucket="data", Key="_copy/sp ace 2.txt")["Body"].read() == b"space\n"


def test_copy_object_missing_source_key(s3):
    with pytest.raises(ClientError) as err:
        s3.copy_object(
            Bucket="data",
            CopySource={"Bucket": "data", "Key": "nope.txt"},
            Key="_copy/nope.txt",
        )
    assert err.value.response["Error"]["Code"] == "NoSuchKey"
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


def test_copy_object_missing_source_bucket(s3):
    with pytest.raises(ClientError) as err:
        s3.copy_object(
            Bucket="data",
            CopySource={"Bucket": "_missing", "Key": "hello.txt"},
            Key="_copy/hello.txt",
        )
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


# --- delete objects (batch) ---


def test_delete_objects_batch(s3):
    s3.put_object(Bucket="data", Key="_del/a.txt", Body=b"a\n")
    s3.put_object(Bucket="data", Key="_del/b.txt", Body=b"b\n")
    resp = s3.delete_objects(
        Bucket="data",
        Delete={"Objects": [{"Key": "_del/a.txt"}, {"Key": "_del/b.txt"}]},
    )
    assert {d["Key"] for d in resp["Deleted"]} == {"_del/a.txt", "_del/b.txt"}
    assert resp.get("Errors", []) == []
    for key in ("_del/a.txt", "_del/b.txt"):
        with pytest.raises(ClientError) as err:
            s3.get_object(Bucket="data", Key=key)
        assert err.value.response["Error"]["Code"] == "NoSuchKey"
    assert s3.list_objects_v2(Bucket="data", Prefix="_del/").get("Contents", []) == []


def test_delete_objects_missing_keys_are_deleted(s3):
    s3.put_object(Bucket="data", Key="_del/one.txt", Body=b"1\n")
    resp = s3.delete_objects(
        Bucket="data",
        Delete={
            "Objects": [
                {"Key": "_del/one.txt"},
                {"Key": "_del/never-existed.txt"},
            ]
        },
    )
    assert {d["Key"] for d in resp["Deleted"]} == {"_del/one.txt", "_del/never-existed.txt"}
    assert resp.get("Errors", []) == []


def test_delete_objects_quiet(s3):
    s3.put_object(Bucket="data", Key="_del/quiet.txt", Body=b"q\n")
    resp = s3.delete_objects(
        Bucket="data",
        Delete={"Objects": [{"Key": "_del/quiet.txt"}], "Quiet": True},
    )
    assert "Deleted" not in resp
    with pytest.raises(ClientError):
        s3.get_object(Bucket="data", Key="_del/quiet.txt")


def test_delete_objects_escaping_key_is_contained(s3):
    # a traversal-y key is an ordinary object in the CSV-backed store (the
    # content path is a flat encoded name), so a batch delete reports it
    # like any other key and nothing can escape the store
    s3.put_object(Bucket="data", Key="../escape.txt", Body=b"stays in\n")
    resp = s3.delete_objects(
        Bucket="data",
        Delete={
            "Objects": [{"Key": "_del/ok.txt"}, {"Key": "../escape.txt"}]
        },
    )
    assert {d["Key"] for d in resp["Deleted"]} == {"_del/ok.txt", "../escape.txt"}
    assert resp.get("Errors", []) == []
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="data", Key="../escape.txt")
    assert err.value.response["Error"]["Code"] == "NoSuchKey"


def test_delete_objects_missing_bucket(s3):
    with pytest.raises(ClientError) as err:
        s3.delete_objects(
            Bucket="_missing",
            Delete={"Objects": [{"Key": "x.txt"}]},
        )
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


# --- conditional requests (If-Match / If-None-Match) ---


def test_get_object_if_match(s3):
    etag = s3.head_object(Bucket="data", Key="hello.txt")["ETag"]
    # a matching ETag lets the request through
    resp = s3.get_object(Bucket="data", Key="hello.txt", IfMatch=etag)
    assert resp["Body"].read() == b"hello from fs-s3\n"

    # '*' matches any existing object
    resp = s3.get_object(Bucket="data", Key="hello.txt", IfMatch="*")
    assert resp["Body"].read() == b"hello from fs-s3\n"

    # a mismatching ETag fails with 412 PreconditionFailed
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="data", Key="hello.txt", IfMatch='"deadbeef"')
    assert err.value.response["Error"]["Code"] == "PreconditionFailed"
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412


def test_get_object_if_none_match(s3):
    etag = s3.head_object(Bucket="data", Key="hello.txt")["ETag"]
    # a matching ETag short-circuits with 304 Not Modified. boto3 raises a
    # ClientError for any status >= 300, so the 304 surfaces as a "304" error.
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="data", Key="hello.txt", IfNoneMatch=etag)
    assert err.value.response["Error"]["Code"] == "304"
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 304

    # a mismatching ETag lets the request through
    resp = s3.get_object(Bucket="data", Key="hello.txt", IfNoneMatch='"deadbeef"')
    assert resp["Body"].read() == b"hello from fs-s3\n"


def test_head_object_conditional_headers(s3):
    etag = s3.head_object(Bucket="data", Key="hello.txt")["ETag"]
    # a matching If-None-Match short-circuits with 304 (raised as a "304" error)
    with pytest.raises(ClientError) as err:
        s3.head_object(Bucket="data", Key="hello.txt", IfNoneMatch=etag)
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 304

    with pytest.raises(ClientError) as err:
        s3.head_object(Bucket="data", Key="hello.txt", IfMatch='"deadbeef"')
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412


# --- put object conditions (If-Match / If-None-Match) ---


def test_put_object_if_none_match_star(s3):
    # the classic create-only-if-absent guard: * matches any existing object
    s3.put_object(Bucket="data", Key="_cond/new.txt", Body=b"one\n", IfNoneMatch="*")

    with pytest.raises(ClientError) as err:
        s3.put_object(Bucket="data", Key="_cond/new.txt", Body=b"two\n", IfNoneMatch="*")
    assert err.value.response["Error"]["Code"] == "PreconditionFailed"
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    # the failed write leaves the original object in place
    assert s3.get_object(Bucket="data", Key="_cond/new.txt")["Body"].read() == b"one\n"


def test_put_object_if_match(s3):
    s3.put_object(Bucket="data", Key="_cond/match.txt", Body=b"first\n")
    etag = s3.head_object(Bucket="data", Key="_cond/match.txt")["ETag"]
    # a matching ETag lets the overwrite through
    s3.put_object(Bucket="data", Key="_cond/match.txt", Body=b"second\n", IfMatch=etag)
    assert s3.get_object(Bucket="data", Key="_cond/match.txt")["Body"].read() == b"second\n"

    # a mismatching ETag fails with 412 and leaves the object untouched
    with pytest.raises(ClientError) as err:
        s3.put_object(Bucket="data", Key="_cond/match.txt", Body=b"third\n", IfMatch='"deadbeef"')
    assert err.value.response["Error"]["Code"] == "PreconditionFailed"
    assert s3.get_object(Bucket="data", Key="_cond/match.txt")["Body"].read() == b"second\n"


def test_put_object_if_match_absent_object(s3):
    # an absent object has no ETag to match, so If-Match always fails
    for cond in ('"anything"', "*"):
        with pytest.raises(ClientError) as err:
            s3.put_object(Bucket="data", Key="_cond/absent.txt", Body=b"x\n", IfMatch=cond)
        assert err.value.response["Error"]["Code"] == "PreconditionFailed"
        assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412


def test_put_object_if_none_match_etag(s3):
    s3.put_object(Bucket="data", Key="_cond/nm.txt", Body=b"one\n")
    etag = s3.head_object(Bucket="data", Key="_cond/nm.txt")["ETag"]
    # a matching ETag blocks the overwrite
    with pytest.raises(ClientError) as err:
        s3.put_object(Bucket="data", Key="_cond/nm.txt", Body=b"two\n", IfNoneMatch=etag)
    assert err.value.response["Error"]["Code"] == "PreconditionFailed"
    assert s3.get_object(Bucket="data", Key="_cond/nm.txt")["Body"].read() == b"one\n"

    # a mismatching ETag lets the overwrite through
    s3.put_object(Bucket="data", Key="_cond/nm.txt", Body=b"two\n", IfNoneMatch='"deadbeef"')
    assert s3.get_object(Bucket="data", Key="_cond/nm.txt")["Body"].read() == b"two\n"


def test_failed_put_leaves_connection_usable(s3):
    # an error returned before the write must still drain the request body,
    # or the next request on the same connection would be mis-framed
    with pytest.raises(ClientError) as err:
        s3.put_object(Bucket="_missing", Key="x.txt", Body=b"data\n")
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"
    assert s3.get_object(Bucket="data", Key="hello.txt")["Body"].read() == b"hello from fs-s3\n"


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

    # removing the object empties the bucket -> it is now deletable
    s3.delete_object(Bucket="_full", Key="x/y.txt")
    assert s3.delete_bucket(Bucket="_full")["ResponseMetadata"]["HTTPStatusCode"] == 204


def test_delete_bucket_missing(s3):
    with pytest.raises(ClientError) as err:
        s3.delete_bucket(Bucket="_missing")
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"


# --- storage layout ---


def test_metadata_in_csv_and_contents_in_data_dir(s3, tmp_path):
    # metadata lives in s3.csv: one row per bucket, one row per object
    with (tmp_path / "s3.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert {r["bucket"] for r in rows if r["kind"] == "bucket"} == {"data"}
    assert {(r["bucket"], r["key"]) for r in rows if r["kind"] == "object"} == {
        ("data", "hello.txt"),
        ("data", "notes/a.md"),
        ("data", "notes/b.txt"),
    }
    # ...and contents live under the data/ subdirectory, one flat file per object
    content = tmp_path / "data" / "data"
    assert (content / "hello.txt").is_file()
    assert (content / "notes%2Fa.md").is_file()
    assert (content / "notes%2Fb.txt").is_file()
