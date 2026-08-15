"""S3-compatible REST routes backed by a local data directory.

Implements just enough of the S3 REST protocol for a boto3 client to
manage, store and retrieve objects.  Buckets are directories under
``DATA_DIR``; a bucket's objects are the files beneath it.  Supported
calls: ListBuckets, CreateBucket, HeadBucket, DeleteBucket, ListObjects
(v1 and v2, with ``Prefix``/``Delimiter``), HeadObject and GetObject
(both honouring the ``Range`` and the ``If-Match``/``If-None-Match``
conditional headers), PutObject, CopyObject, DeleteObjects
and DeleteObject.  CopyObject is a ``PutObject`` that carries the
``x-amz-copy-source`` header; it copies the source object's bytes to the
destination, giving the new object a fresh ``LastModified``.  DeleteObjects
is the ``?delete=`` batch endpoint: it removes several keys in one request,
reporting each as ``Deleted`` (``Error`` for a key that escapes the bucket).
On a ``PutObject`` the ``If-Match``/``If-None-Match`` headers guard the
write instead: any failed precondition aborts it with 412
``PreconditionFailed`` (``If-None-Match: *`` is the usual
create-only-if-absent guard).

Everything is read from, and written to, the filesystem on every
request - no state, no cache.  Request signatures are accepted but
not verified.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import unquote
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request, Response

from aws.settings import DATA_DIR

S3_NS = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'

router = APIRouter()


def _bucket_dir(bucket: str) -> Path | None:
    """Bucket name -> the directory under DATA_DIR, or None if it escapes it."""
    p = (DATA_DIR / bucket).resolve()
    try:
        p.relative_to(DATA_DIR)
    except ValueError:
        return None
    return p


def _meta(p: Path) -> dict:
    st = p.stat()
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return {
        "size": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, UTC),
        "etag": h.hexdigest(),
        "type": mimetypes.guess_type(p.name)[0] or "application/octet-stream",
    }


def _content(key: str, m: dict) -> str:
    iso = m["mtime"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return (f"<Contents><Key>{escape(key)}</Key><LastModified>{iso}</LastModified>"
            f"<ETag>&quot;{m['etag']}&quot;</ETag><Size>{m['size']}</Size>"
            "<StorageClass>STANDARD</StorageClass></Contents>")


def _walk(bucket: str, prefix: str, delimiter: str | None) -> tuple[list[tuple[str, dict]], list[str]]:
    base = _bucket_dir(bucket)
    objects = []
    prefixes = set()
    if base is None or not base.is_dir():
        return objects, sorted(prefixes)
    for root, dirs, files in os.walk(base):
        dirs.sort()
        files.sort()
        for name in files:
            rel = (Path(root) / name).relative_to(base).as_posix()
            if not rel.startswith(prefix):
                continue
            rest = rel[len(prefix):]
            if delimiter and delimiter in rest:
                prefixes.add(prefix + rest.split(delimiter, 1)[0] + delimiter)
                continue
            objects.append((rel, _meta(Path(root) / name)))
    return objects, sorted(prefixes)


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
    buckets = []
    for p in sorted(DATA_DIR.iterdir(), key=lambda x: x.name):
        if not p.is_dir():
            continue
        created = datetime.fromtimestamp(p.stat().st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        buckets.append(f"<Bucket><Name>{escape(p.name)}</Name><CreationDate>{created}</CreationDate></Bucket>")
    xml = (f"<ListAllMyBucketsResult {S3_NS}><Owner><ID>local</ID></Owner>"
           f"<Buckets>{''.join(buckets)}</Buckets></ListAllMyBucketsResult>")
    return Response(xml, media_type="application/xml")


@router.put("/{bucket}")
async def create_bucket(bucket: str) -> Response:
    base = _bucket_dir(bucket)
    if base is None:
        return _error(400, "InvalidBucketName", "The specified bucket is not valid.")
    base.mkdir(parents=True, exist_ok=True)
    return Response(status_code=200, headers={"Location": f"/{bucket}"})


@router.head("/{bucket}")
async def head_bucket(bucket: str) -> Response:
    base = _bucket_dir(bucket)
    if base is None or not base.is_dir():
        return Response(status_code=404)
    return Response(status_code=200)


@router.get("/{bucket}")
async def list_bucket_objects(request: Request, bucket: str) -> Response:
    base = _bucket_dir(bucket)
    if base is None:
        return _error(400, "InvalidBucketName", "The specified bucket is not valid.")
    if not base.is_dir():
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    prefix = request.query_params.get("prefix", "")
    delimiter = request.query_params.get("delimiter")
    objects, prefixes = _walk(bucket, prefix, delimiter)
    if request.query_params.get("list-type") == "2":
        xml = _list_v2_xml(bucket, prefix, objects, prefixes)
    else:
        xml = _list_v1_xml(bucket, prefix, objects)
    return Response(xml, media_type="application/xml")


@router.delete("/{bucket}")
async def delete_bucket(bucket: str) -> Response:
    base = _bucket_dir(bucket)
    if base is None:
        return _error(400, "InvalidBucketName", "The specified bucket is not valid.")
    if not base.is_dir():
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    if any(p.is_file() for p in base.rglob("*")):
        return _error(409, "BucketNotEmpty", "The bucket you tried to delete is not empty.")
    shutil.rmtree(base)
    return Response(status_code=204)


def _object_path(bucket: str, key: str) -> Path | Response:
    """Resolve a key inside a bucket, or return an S3 error response."""
    base = _bucket_dir(bucket)
    if base is None:
        return _error(400, "InvalidBucketName", "The specified bucket is not valid.")
    if not base.is_dir():
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    p = (base / key).resolve()
    try:
        p.relative_to(base)
    except ValueError:
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    return p


def _object_headers(m: dict) -> dict:
    return {
        "ETag": f'"{m["etag"]}"',
        "Content-Type": m["type"],
        "Last-Modified": format_datetime(m["mtime"]),
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
                "Last-Modified": format_datetime(m["mtime"]),
            },
        )
    return None


def _put_precondition_response(request: Request, path: Path) -> Response | None:
    """Evaluate the If-Match / If-None-Match headers for a ``PutObject``.

    A failed precondition returns a 412 ``PreconditionFailed``; None means
    the write may proceed.  An absent object has no ETag, so ``If-Match`` can
    never succeed on it, while ``If-None-Match: *`` is the usual
    create-only-if-absent guard.  ``If-Match`` is evaluated first.
    """
    if_match = request.headers.get("if-match")
    if if_match is None and request.headers.get("if-none-match") is None:
        return None
    existing_etag = _meta(path)["etag"] if path.is_file() else None
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

    src = _object_path(src_bucket, src_key)
    if isinstance(src, Response):
        return src
    if not src.is_file():
        return _error(404, "NoSuchKey", "The specified key does not exist.")

    dest = _object_path(bucket, key)
    if isinstance(dest, Response):
        return dest
    if src != dest:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    m = _meta(dest)
    iso = m["mtime"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    body = (f"<CopyObjectResult {S3_NS}><ETag>&quot;{m['etag']}&quot;</ETag>"
            f"<LastModified>{iso}</LastModified></CopyObjectResult>")
    return Response(
        body,
        status_code=200,
        headers={"ETag": f'"{m["etag"]}"', "Last-Modified": format_datetime(m["mtime"])},
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
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    pre = _put_precondition_response(request, p)
    if pre is not None:
        return pre
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    etag = hashlib.md5(data).hexdigest()
    return Response(
        f'<PutObjectResult {S3_NS}><ETag>&quot;{etag}&quot;</ETag></PutObjectResult>',
        status_code=200,
        headers={"ETag": f'"{etag}"'},
        media_type="application/xml",
    )


@router.head("/{bucket}/{key:path}")
async def head_object(request: Request, bucket: str, key: str) -> Response:
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    if not p.is_file():
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    m = _meta(p)
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
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    if not p.is_file():
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    m = _meta(p)
    pre = _precondition_response(request, m)
    if pre is not None:
        return pre
    headers = _object_headers(m)
    headers["Accept-Ranges"] = "bytes"
    try:
        span = _parse_range(request.headers.get("range"), m["size"])
    except ValueError:
        return _range_not_satisfiable(m["size"])
    if span is None:
        return Response(p.read_bytes(), headers=headers, media_type=m["type"])
    start, end = span
    with p.open("rb") as f:
        f.seek(start)
        data = f.read(end - start + 1)
    headers["Content-Range"] = f"bytes {start}-{end}/{m['size']}"
    headers["Content-Length"] = str(len(data))
    return Response(data, status_code=206, headers=headers, media_type=m["type"])


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
    base = _bucket_dir(bucket)
    if base is None:
        return _error(400, "InvalidBucketName", "The specified bucket is not valid.")
    if not base.is_dir():
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")

    body = await request.body()
    keys, quiet = _parse_delete_body(body)
    if keys is None:
        return _error(400, "MalformedXML", "The XML you provided was not well-formed.")

    deleted: list[str] = []
    errors: list[tuple[str, str, str]] = []
    for key in keys:
        p = _object_path(bucket, key)
        if isinstance(p, Response):
            # the bucket is valid, so the only error here is an escaping key
            errors.append((key, "NoSuchKey", "The specified key does not exist."))
            continue
        p.unlink(missing_ok=True)  # idempotent, like DeleteObject
        deleted.append(key)

    if quiet:
        return Response(status_code=200)

    parts = [f"<DeleteResult {S3_NS}>"]
    parts += [f"<Deleted><Key>{escape(k)}</Key></Deleted>" for k in deleted]
    parts += [
        f"<Error><Key>{escape(k)}</Key><Code>{code}</Code><Message>{escape(message)}</Message></Error>"
        for (k, code, message) in errors
    ]
    parts.append("</DeleteResult>")
    return Response("".join(parts), media_type="application/xml")


@router.delete("/{bucket}/{key:path}")
async def delete_object(bucket: str, key: str) -> Response:
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    if not p.is_dir():
        p.unlink(missing_ok=True)  # idempotent, like S3
    return Response(status_code=204)
