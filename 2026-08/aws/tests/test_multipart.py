"""Pytest suite for multipart uploads, driving the API with a real boto3
client over HTTP.

Same harness as test_s3.py: each test runs against a fresh server started
in-process (uvicorn in a background thread) with the store mocked to an
isolated temporary directory, so tests are hermetic and never touch the
checked-in ``data/`` directory.

Run from the project root::

    pytest tests/test_multipart.py
"""

import hashlib
import os
import socket
import threading
import time
import urllib.request

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
    backing = S3Store(tmp_path)
    backing.create_bucket("mp")
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


# --- the full lifecycle ---


def test_multipart_happy_path(s3):
    upload_id = s3.create_multipart_upload(Bucket="mp", Key="big.bin")["UploadId"]
    parts = [b"a" * 1024, b"b" * 512, b"c"]
    uploaded = []
    for number, body in enumerate(parts, start=1):
        etag = s3.upload_part(
            Bucket="mp", Key="big.bin", PartNumber=number,
            UploadId=upload_id, Body=body,
        )["ETag"]
        uploaded.append((number, etag))

    listed = s3.list_parts(Bucket="mp", Key="big.bin", UploadId=upload_id)["Parts"]
    assert [p["PartNumber"] for p in listed] == [1, 2, 3]
    assert [p["Size"] for p in listed] == [1024, 512, 1]
    assert [p["ETag"] for p in listed] == [t for _, t in uploaded]

    # S3's multipart ETag: the MD5 of the parts' MD5 digests, suffixed -N.
    digest = hashlib.md5()
    for _, etag in uploaded:
        digest.update(bytes.fromhex(etag.strip('"')))
    completed = s3.complete_multipart_upload(
        Bucket="mp", Key="big.bin", UploadId=upload_id,
        MultipartUpload={"Parts": [{"PartNumber": n, "ETag": t} for n, t in uploaded]},
    )
    assert completed["ETag"].strip('"') == f"{digest.hexdigest()}-3"

    assert s3.get_object(Bucket="mp", Key="big.bin")["Body"].read() == b"".join(parts)
    assert s3.head_object(Bucket="mp", Key="big.bin")["ContentLength"] == sum(map(len, parts))

    # a completed upload is gone: its parts no longer list
    with pytest.raises(ClientError) as err:
        s3.list_parts(Bucket="mp", Key="big.bin", UploadId=upload_id)
    assert err.value.response["Error"]["Code"] == "NoSuchUpload"


def test_upload_part_reupload_overwrites(s3):
    upload_id = s3.create_multipart_upload(Bucket="mp", Key="r.bin")["UploadId"]
    first = s3.upload_part(Bucket="mp", Key="r.bin", PartNumber=1, UploadId=upload_id,
                           Body=b"one")["ETag"]
    second = s3.upload_part(Bucket="mp", Key="r.bin", PartNumber=1, UploadId=upload_id,
                            Body=b"two")["ETag"]
    assert first != second

    listed = s3.list_parts(Bucket="mp", Key="r.bin", UploadId=upload_id)["Parts"]
    assert [p["PartNumber"] for p in listed] == [1]
    assert [p["Size"] for p in listed] == [3]

    s3.complete_multipart_upload(
        Bucket="mp", Key="r.bin", UploadId=upload_id,
        MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": second}]},
    )
    assert s3.get_object(Bucket="mp", Key="r.bin")["Body"].read() == b"two"


def test_upload_part_copy(s3):
    # UploadPartCopy: the part's bytes come from the source object, and the
    # destination object only materialises when the upload completes
    source = b"part copy payload\n" * 64
    s3.put_object(Bucket="mp", Key="src.bin", Body=source)

    upload_id = s3.create_multipart_upload(Bucket="mp", Key="dst.bin")["UploadId"]
    # botocore nests UploadPartCopy's result: ETag lives under CopyPartResult
    copied = s3.upload_part_copy(
        Bucket="mp", Key="dst.bin", PartNumber=1, UploadId=upload_id,
        CopySource={"Bucket": "mp", "Key": "src.bin"},
    )
    etag = copied["CopyPartResult"]["ETag"]
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="mp", Key="dst.bin")
    assert err.value.response["Error"]["Code"] == "NoSuchKey"

    parts = s3.list_parts(Bucket="mp", Key="dst.bin", UploadId=upload_id)["Parts"]
    assert [(p["PartNumber"], p["Size"]) for p in parts] == [(1, len(source))]

    s3.complete_multipart_upload(
        Bucket="mp", Key="dst.bin", UploadId=upload_id,
        MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": etag}]},
    )
    assert s3.get_object(Bucket="mp", Key="dst.bin")["Body"].read() == source
    assert s3.get_object(Bucket="mp", Key="src.bin")["Body"].read() == source


def test_upload_part_copy_missing_source(s3):
    upload_id = s3.create_multipart_upload(Bucket="mp", Key="dst.bin")["UploadId"]
    with pytest.raises(ClientError) as err:
        s3.upload_part_copy(
            Bucket="mp", Key="dst.bin", PartNumber=1, UploadId=upload_id,
            CopySource={"Bucket": "mp", "Key": "absent.bin"},
        )
    assert err.value.response["Error"]["Code"] == "NoSuchKey"
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="mp", Key="dst.bin")
    assert err.value.response["Error"]["Code"] == "NoSuchKey"


def test_multipart_metadata_from_create(s3):
    # like S3, a multipart upload's user-defined metadata is set on the
    # create request and lands on the object at completion
    upload_id = s3.create_multipart_upload(
        Bucket="mp", Key="m.bin", Metadata={"owner": "ada"})["UploadId"]
    etag = s3.upload_part(Bucket="mp", Key="m.bin", PartNumber=1,
                          UploadId=upload_id, Body=b"z")["ETag"]
    s3.complete_multipart_upload(
        Bucket="mp", Key="m.bin", UploadId=upload_id,
        MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": etag}]})
    assert s3.head_object(Bucket="mp", Key="m.bin")["Metadata"] == {"owner": "ada"}


def test_abort_multipart_upload(s3):
    upload_id = s3.create_multipart_upload(Bucket="mp", Key="gone.bin")["UploadId"]
    s3.upload_part(Bucket="mp", Key="gone.bin", PartNumber=1, UploadId=upload_id, Body=b"x")
    s3.abort_multipart_upload(Bucket="mp", Key="gone.bin", UploadId=upload_id)

    with pytest.raises(ClientError) as err:
        s3.list_parts(Bucket="mp", Key="gone.bin", UploadId=upload_id)
    assert err.value.response["Error"]["Code"] == "NoSuchUpload"
    with pytest.raises(ClientError) as err:
        s3.get_object(Bucket="mp", Key="gone.bin")
    assert err.value.response["Error"]["Code"] == "NoSuchKey"
    assert s3.list_objects_v2(Bucket="mp")["KeyCount"] == 0


# --- listing in-flight uploads ---


def test_list_multipart_uploads(s3):
    for key in ("a/one.bin", "a/two.bin", "b.bin"):
        s3.create_multipart_upload(Bucket="mp", Key=key)
    # a finished object is not in-flight, so it must not appear
    s3.put_object(Bucket="mp", Key="done.bin", Body=b"done")

    result = s3.list_multipart_uploads(Bucket="mp")
    assert sorted(u["Key"] for u in result["Uploads"]) == ["a/one.bin", "a/two.bin", "b.bin"]
    assert result["IsTruncated"] is False
    assert result["MaxUploads"] == 1000
    assert all(u["StorageClass"] == "STANDARD" for u in result["Uploads"])
    assert all(u["Initiated"] for u in result["Uploads"])


def test_list_multipart_uploads_prefix_and_delimiter(s3):
    for key in ("d/a/1.bin", "d/a/2.bin", "d/b/3.bin", "e/4.bin", "root.bin"):
        s3.create_multipart_upload(Bucket="mp", Key=key)

    prefixed = s3.list_multipart_uploads(Bucket="mp", Prefix="d/")
    assert sorted(u["Key"] for u in prefixed["Uploads"]) == [
        "d/a/1.bin", "d/a/2.bin", "d/b/3.bin"]

    delim = s3.list_multipart_uploads(Bucket="mp", Delimiter="/")
    assert [cp["Prefix"] for cp in delim["CommonPrefixes"]] == ["d/", "e/"]
    assert [u["Key"] for u in delim.get("Uploads", [])] == ["root.bin"]


def test_list_multipart_uploads_pagination(s3):
    ids = [
        s3.create_multipart_upload(Bucket="mp", Key=f"pg/{i:02d}.bin")["UploadId"]
        for i in range(5)
    ]

    first = s3.list_multipart_uploads(Bucket="mp", Prefix="pg/", MaxUploads=2)
    assert [u["Key"] for u in first["Uploads"]] == ["pg/00.bin", "pg/01.bin"]
    assert first["IsTruncated"] is True
    assert first["NextKeyMarker"] == "pg/01.bin"
    assert first["NextUploadIdMarker"] == ids[1]

    last = s3.list_multipart_uploads(
        Bucket="mp", Prefix="pg/",
        KeyMarker=first["NextKeyMarker"], UploadIdMarker=first["NextUploadIdMarker"])
    assert [u["Key"] for u in last["Uploads"]] == ["pg/02.bin", "pg/03.bin", "pg/04.bin"]
    assert last["IsTruncated"] is False
    assert "NextKeyMarker" not in last


def test_list_multipart_uploads_paginator(s3):
    for i in range(5):
        s3.create_multipart_upload(Bucket="mp", Key=f"pn/{i:02d}.bin")

    keys = [u["Key"]
            for page in s3.get_paginator("list_multipart_uploads").paginate(
                Bucket="mp", Prefix="pn/", PaginationConfig={"PageSize": 2})
            for u in page.get("Uploads", [])]
    assert keys == [f"pn/{i:02d}.bin" for i in range(5)]


def test_list_multipart_uploads_then_abort_all(s3):
    # the listing is what makes orphaned uploads cleanable through the API
    for key in ("c/x.bin", "c/y.bin"):
        s3.create_multipart_upload(Bucket="mp", Key=key)

    uploads = s3.list_multipart_uploads(Bucket="mp").get("Uploads", [])
    assert sorted(u["Key"] for u in uploads) == ["c/x.bin", "c/y.bin"]
    for upload in uploads:
        s3.abort_multipart_upload(Bucket="mp", Key=upload["Key"], UploadId=upload["UploadId"])

    assert s3.list_multipart_uploads(Bucket="mp").get("Uploads", []) == []


# --- errors ---


def test_upload_part_unknown_upload(s3):
    with pytest.raises(ClientError) as err:
        s3.upload_part(Bucket="mp", Key="k", PartNumber=1, UploadId="f" * 32, Body=b"x")
    assert err.value.response["Error"]["Code"] == "NoSuchUpload"


def test_abort_missing_upload(s3):
    with pytest.raises(ClientError) as err:
        s3.abort_multipart_upload(Bucket="mp", Key="k", UploadId="f" * 32)
    assert err.value.response["Error"]["Code"] == "NoSuchUpload"


def test_complete_with_wrong_etag(s3):
    upload_id = s3.create_multipart_upload(Bucket="mp", Key="bad.bin")["UploadId"]
    s3.upload_part(Bucket="mp", Key="bad.bin", PartNumber=1, UploadId=upload_id, Body=b"one")
    with pytest.raises(ClientError) as err:
        s3.complete_multipart_upload(
            Bucket="mp", Key="bad.bin", UploadId=upload_id,
            MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": "0" * 32}]},
        )
    assert err.value.response["Error"]["Code"] == "InvalidPart"
    # a failed complete leaves the upload intact
    assert s3.list_parts(Bucket="mp", Key="bad.bin", UploadId=upload_id)["Parts"]


def test_complete_with_out_of_order_parts(s3):
    upload_id = s3.create_multipart_upload(Bucket="mp", Key="order.bin")["UploadId"]
    etag1 = s3.upload_part(Bucket="mp", Key="order.bin", PartNumber=1,
                           UploadId=upload_id, Body=b"one")["ETag"]
    etag2 = s3.upload_part(Bucket="mp", Key="order.bin", PartNumber=2,
                           UploadId=upload_id, Body=b"two")["ETag"]
    with pytest.raises(ClientError) as err:
        s3.complete_multipart_upload(
            Bucket="mp", Key="order.bin", UploadId=upload_id,
            MultipartUpload={"Parts": [
                {"PartNumber": 2, "ETag": etag2},
                {"PartNumber": 1, "ETag": etag1},
            ]},
        )
    assert err.value.response["Error"]["Code"] == "InvalidPartOrder"


def test_missing_bucket_multipart(s3):
    with pytest.raises(ClientError) as err:
        s3.create_multipart_upload(Bucket="_missing", Key="k")
    assert err.value.response["Error"]["Code"] == "NoSuchBucket"


# --- end-to-end: boto3's managed transfer ---


def test_managed_transfer_drives_multipart(s3, tmp_path):
    """boto3's managed transfer switches to multipart above its 8 MiB
    threshold, so this exercises the whole flow the way a real client does."""
    body = os.urandom(20 * 1024 * 1024)  # 20 MiB -> three 8 MiB parts (plus 4)
    src = tmp_path / "src.bin"
    src.write_bytes(body)
    s3.upload_file(str(src), "mp", "managed.bin")
    assert s3.get_object(Bucket="mp", Key="managed.bin")["Body"].read() == body
