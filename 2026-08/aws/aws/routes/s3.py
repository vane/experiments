"""S3-compatible REST routes backed by a CSV metadata store.

Implements just enough of the S3 REST protocol for a boto3 client to
manage, store and retrieve objects.  Metadata (one row per bucket and
per object: last-modified, size, ETag, content type) lives in the CSV
file ``s3.csv`` under the data directory, and object contents live as
flat files under its ``data/`` subdirectory (see ``aws/service/s3.py``).
Listings are computed from the CSV, so no filesystem walking is
involved and a key can never escape the store.  Supported calls:
ListBuckets, CreateBucket, HeadBucket, DeleteBucket, ListObjects
(v1 and v2, with ``Prefix``/``Delimiter``), HeadObject and GetObject
(both honouring the ``Range`` and the ``If-Match``/``If-None-Match``
conditional headers), PutObject, CopyObject, DeleteObjects
and DeleteObject.  CopyObject is a ``PutObject`` that carries the
``x-amz-copy-source`` header; it copies the source object's bytes to the
destination, giving the new object a fresh ``LastModified``.  DeleteObjects
is the ``?delete=`` batch endpoint: it removes several keys in one request,
reporting each as ``Deleted``.  On a ``PutObject`` the
``If-Match``/``If-None-Match`` headers guard the write instead: any failed
precondition aborts it with 412 ``PreconditionFailed`` (``If-None-Match: *``
is the usual create-only-if-absent guard).

Every request reads the CSV and the content files it names - no cache,
no background indexing.  Request signatures are accepted but not
verified.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import format_datetime
from urllib.parse import unquote
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request, Response

from aws.settings import DATA_DIR
from aws.service.s3 import S3Store

S3_NS = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'

router = APIRouter()

# The CSV-backed store; tests swap this out for an isolated temporary store.
store = S3Store(DATA_DIR)


def _iso_z(dt: datetime) -> str:
    """A datetime in S3's ISO-8601 UTC form (millisecond precision)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _content(key: str, m: dict) -> str:
    iso = _iso_z(m["last_modified"])
    return (f"<Contents><Key>{escape(key)}</Key><LastModified>{iso}</LastModified>"
            f"<ETag>&quot;{m['etag']}&quot;</ETag><Size>{m['size']}</Size>"
            "<StorageClass>STANDARD</StorageClass></Contents>")


def _list_v2_xml(name: str, prefix: str, objects: list, prefixes: list) -> str:
    parts = [f"<ListBucketResult {S3_NS}><Name>{escape(name)}</Name><Prefix>{escape(prefix)}</Prefix>",
             f"<KeyCount>{len(objects) + len(prefixes)}</KeyCount><MaxKeys>1000</MaxKeys>",
             "<IsTruncated>false</IsTruncated>"]
    parts += [f"<CommonPrefixes><Prefix>{escape(p)}</Prefix></CommonPrefixes>" for p in prefixes]
    parts += [_content(k, m) for k, m in objects]
    parts.append("</ListBucketResult>")
    return "".join(parts)


def _list_v1_xml(name: str, prefix: str, objects: list) -> str:
    parts = [f"<ListBucketResult {S3_NS}><Name>{escape(name)}</Name><Prefix>{escape(prefix)}</Prefix>",
             "<Marker></Marker><MaxKeys>1000</MaxKeys><IsTruncated>false</IsTruncated>"]
    parts += [_content(k, m) for k, m in objects]
    parts.append("</ListBucketResult>")
    return "".join(parts)


def _error(status: int, code: str, message: str) -> Response:
    return Response(f"<Error><Code>{code}</Code><Message>{escape(message)}</Message></Error>",
                    status_code=status, media_type="application/xml")


@router.get("/")
async def list_buckets() -> Response:
    buckets = [
        f"<Bucket><Name>{escape(name)}</Name><CreationDate>{_iso_z(created)}</CreationDate></Bucket>"
        for name, created in store.list_buckets()
    ]
    xml = (f"<ListAllMyBucketsResult {S3_NS}><Owner><ID>local</ID></Owner>"
           f"<Buckets>{''.join(buckets)}</Buckets></ListAllMyBucketsResult>")
    return Response(xml, media_type="application/xml")


@router.put("/{bucket}")
async def create_bucket(bucket: str) -> Response:
    if not store.create_bucket(bucket):
        return _error(400, "InvalidBucketName", "The specified bucket is not valid.")
    return Response(status_code=200, headers={"Location": f"/{bucket}"})


@router.head("/{bucket}")
async def head_bucket(bucket: str) -> Response:
    if not store.bucket_exists(bucket):
        return Response(status_code=404)
    return Response(status_code=200)


@router.get("/{bucket}")
async def list_bucket_objects(request: Request, bucket: str) -> Response:
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    prefix = request.query_params.get("prefix", "")
    delimiter = request.query_params.get("delimiter")
    objects, prefixes = store.list_objects(bucket, prefix, delimiter)
    if request.query_params.get("list-type") == "2":
        xml = _list_v2_xml(bucket, prefix, objects, prefixes)
    else:
        xml = _list_v1_xml(bucket, prefix, objects)
    return Response(xml, media_type="application/xml")


@router.delete("/{bucket}")
async def delete_bucket(bucket: str) -> Response:
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    if store.object_count(bucket):
        return _error(409, "BucketNotEmpty", "The bucket you tried to delete is not empty.")
    store.delete_bucket(bucket)
    return Response(status_code=204)


def _object_headers(m: dict) -> dict:
    return {
        "ETag": f'"{m["etag"]}"',
        "Content-Type": m["content_type"],
        "Last-Modified": format_datetime(m["last_modified"]),
        "Content-Length": str(m["size"]),
    }


def _parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Resolve a ``Range`` header against a file of ``size`` bytes.

    Returns the inclusive (start, end) span for the ``bytes=start-end``,
    ``bytes=start-`` and ``bytes=-suffix`` forms, or None when the header
    is absent.  Raises ValueError for malformed or unsatisfiable ranges.
    """
    if header is None:
        return None
    match = re.fullmatch(r"bytes\s*=\s*(\d*)\s*-\s*(\d*)", header.strip(), re.IGNORECASE)
    if match is None or (match[1] == "" and match[2] == ""):
        raise ValueError("malformed range")
    start_s, end_s = match.groups()
    if start_s:
        start = int(start_s)
        end = int(end_s) if end_s else size - 1
    else:  # suffix range: the last N bytes
        if int(end_s) == 0:
            raise ValueError("unsatisfiable range")
        start, end = max(size - int(end_s), 0), size - 1
    if start > end or start >= size:
        raise ValueError("unsatisfiable range")
    return start, end


def _range_not_satisfiable(size: int) -> Response:
    """416 for a malformed or unsatisfiable ``Range`` header."""
    resp = _error(416, "InvalidRange", "Requested range not satisfied.")
    resp.headers["Content-Range"] = f"bytes */{size}"
    return resp


def _etag_matches(value: str, etag: str) -> bool:
    """Whether an object with ``etag`` matches an If-Match/If-None-Match value.

    ``*`` matches any object, and a comma-separated list matches if any entry
    matches.  Surrounding double quotes on each entry are ignored, so both the
    quoted form S3 uses (``"abc123"``) and a bare value work.
    """
    value = value.strip()
    if value == "*":
        return True
    return any(
        entry.strip().strip('"') == etag for entry in value.split(",") if entry.strip()
    )


def _precondition_failed() -> Response:
    """412 for a failed If-Match / If-None-Match precondition."""
    return _error(
        412, "PreconditionFailed",
        "At least one of the preconditions you specified did not hold",
    )


def _precondition_response(request: Request, m: dict) -> Response | None:
    """Evaluate the If-Match / If-None-Match headers against an existing object.

    Returns a 412 ``PreconditionFailed`` when ``If-Match`` does not match, a
    304 ``Not Modified`` when ``If-None-Match`` does, or None when both hold
    (the request then proceeds as usual).  ``If-Match`` is evaluated first,
    per HTTP semantics.
    """
    if_match = request.headers.get("if-match")
    if if_match is not None and not _etag_matches(if_match, m["etag"]):
        return _precondition_failed()
    if_none_match = request.headers.get("if-none-match")
    if if_none_match is not None and _etag_matches(if_none_match, m["etag"]):
        return Response(
            status_code=304,
            headers={
                "ETag": f'"{m["etag"]}"',
                "Last-Modified": format_datetime(m["last_modified"]),
            },
        )
    return None


def _put_precondition_response(request: Request, existing_etag: str | None) -> Response | None:
    """Evaluate the If-Match / If-None-Match headers for a ``PutObject``.

    A failed precondition returns a 412 ``PreconditionFailed``; None means
    the write may proceed.  An absent object has no ETag, so ``If-Match`` can
    never succeed on it, while ``If-None-Match: *`` is the usual
    create-only-if-absent guard.  ``If-Match`` is evaluated first.
    """
    if_match = request.headers.get("if-match")
    if if_match is None and request.headers.get("if-none-match") is None:
        return None
    if if_match is not None and (
        existing_etag is None or not _etag_matches(if_match, existing_etag)
    ):
        return _precondition_failed()
    if_none_match = request.headers.get("if-none-match")
    if (
        if_none_match is not None
        and existing_etag is not None
        and _etag_matches(if_none_match, existing_etag)
    ):
        return _precondition_failed()
    return None


def _parse_copy_source(header: str) -> tuple[str, str] | None:
    """Split an ``x-amz-copy-source`` header into ``(bucket, key)``.

    The header is ``{source_bucket}/{source_key}`` (optionally with a leading
    slash); the key is percent-encoded.  Returns None when the header names no
    bucket and key.
    """
    value = header.strip().removeprefix("/")
    value = value.split("?", 1)[0]  # a versionId suffix is not supported
    if "/" not in value:
        return None
    bucket, key = value.split("/", 1)
    bucket, key = unquote(bucket), unquote(key)
    if not bucket or not key:
        return None
    return bucket, key


def _copy_object(bucket: str, key: str, source: str) -> Response:
    """CopyObject: copy the source object's bytes to ``{bucket}/{key}``."""
    parsed = _parse_copy_source(source)
    if parsed is None:
        return _error(400, "InvalidArgument", "The x-amz-copy-source header is malformed.")
    src_bucket, src_key = parsed
    if not store.bucket_exists(src_bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    if store.object_meta(src_bucket, src_key) is None:
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    m = store.copy_object(src_bucket, src_key, bucket, key)
    body = (f"<CopyObjectResult {S3_NS}><ETag>&quot;{m['etag']}&quot;</ETag>"
            f"<LastModified>{_iso_z(m['last_modified'])}</LastModified></CopyObjectResult>")
    return Response(
        body,
        status_code=200,
        headers={"ETag": f'"{m["etag"]}"', "Last-Modified": format_datetime(m["last_modified"])},
        media_type="application/xml",
    )


@router.put("/{bucket}/{key:path}")
async def put_object(request: Request, bucket: str, key: str) -> Response:
    copy_source = request.headers.get("x-amz-copy-source")
    if copy_source is not None:
        return _copy_object(bucket, key, copy_source)
    # read the body up front: an unread body would desync a keep-alive
    # connection if an error is returned before the write
    data = await request.body()
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    existing = store.object_meta(bucket, key)
    pre = _put_precondition_response(request, existing["etag"] if existing is not None else None)
    if pre is not None:
        return pre
    m = store.put_object(bucket, key, data)
    return Response(
        f'<PutObjectResult {S3_NS}><ETag>&quot;{m["etag"]}&quot;</ETag></PutObjectResult>',
        status_code=200,
        headers={"ETag": f'"{m["etag"]}"'},
        media_type="application/xml",
    )


@router.head("/{bucket}/{key:path}")
async def head_object(request: Request, bucket: str, key: str) -> Response:
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    m = store.object_meta(bucket, key)
    if m is None:
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    pre = _precondition_response(request, m)
    if pre is not None:
        return pre
    headers = _object_headers(m)
    headers["Accept-Ranges"] = "bytes"
    try:
        span = _parse_range(request.headers.get("range"), m["size"])
    except ValueError:
        return _range_not_satisfiable(m["size"])
    if span is not None:
        headers["Content-Range"] = f"bytes {span[0]}-{span[1]}/{m['size']}"
        headers["Content-Length"] = str(span[1] - span[0] + 1)
        status = 206
    else:
        status = 200
    return Response(status_code=status, headers=headers)


@router.get("/{bucket}/{key:path}")
async def get_object(request: Request, bucket: str, key: str) -> Response:
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    m = store.object_meta(bucket, key)
    if m is None:
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    pre = _precondition_response(request, m)
    if pre is not None:
        return pre
    headers = _object_headers(m)
    headers["Accept-Ranges"] = "bytes"
    try:
        span = _parse_range(request.headers.get("range"), m["size"])
    except ValueError:
        return _range_not_satisfiable(m["size"])
    path = store.content_path(bucket, key)
    if span is None:
        return Response(path.read_bytes(), headers=headers, media_type=m["content_type"])
    start, end = span
    with path.open("rb") as f:
        f.seek(start)
        data = f.read(end - start + 1)
    headers["Content-Range"] = f"bytes {start}-{end}/{m['size']}"
    headers["Content-Length"] = str(len(data))
    return Response(data, status_code=206, headers=headers, media_type=m["content_type"])


def _local(tag: str) -> str:
    """Strip an XML namespace (``{uri}name`` -> ``name``)."""
    return tag.rsplit("}", 1)[-1]


def _parse_delete_body(body: bytes) -> tuple[list[str] | None, bool]:
    """Parse a ``?delete=`` request body into ``(keys, quiet)``.

    The body is ``<Delete><Object><Key>…</Key></Object>…[<Quiet>true</Quiet>]
    </Delete>`` (namespaced).  Returns ``(None, False)`` when the body is not
    well-formed XML.
    """
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None, False
    keys: list[str] = []
    quiet = False
    for el in root.iter():
        name = _local(el.tag)
        if name == "Object":
            for child in el:
                if _local(child.tag) == "Key":
                    keys.append(child.text or "")
        elif name == "Quiet":
            quiet = (el.text or "").strip().lower() == "true"
    return keys, quiet


@router.post("/{bucket}")
async def delete_objects(request: Request, bucket: str) -> Response:
    """DeleteObjects: remove several keys in one ``?delete=`` request."""
    if "delete" not in request.query_params:
        return _error(400, "InvalidRequest", "Expected a batch-delete request.")
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")

    body = await request.body()
    keys, quiet = _parse_delete_body(body)
    if keys is None:
        return _error(400, "MalformedXML", "The XML you provided was not well-formed.")

    deleted = store.delete_objects(bucket, keys)

    if quiet:
        return Response(status_code=200)

    parts = [f"<DeleteResult {S3_NS}>"]
    parts += [f"<Deleted><Key>{escape(k)}</Key></Deleted>" for k in deleted]
    parts.append("</DeleteResult>")
    return Response("".join(parts), media_type="application/xml")


@router.delete("/{bucket}/{key:path}")
async def delete_object(bucket: str, key: str) -> Response:
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    store.delete_object(bucket, key)
    return Response(status_code=204)
