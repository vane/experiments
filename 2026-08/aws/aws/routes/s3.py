"""S3-compatible REST routes backed by a parquet metadata store.

Implements just enough of the S3 REST protocol for a boto3 client to
manage, store and retrieve objects.  Metadata (one row per bucket and
per object: last-modified, size, ETag, content type, user-defined
metadata) lives in the parquet file ``s3.parquet`` under the data
directory, and object contents live as flat files under its ``data/``
subdirectory (see ``aws/service/s3.py``).  Listings are computed from the
index, so no filesystem walking is involved and a key can never escape
the store.  Supported calls:
ListBuckets, CreateBucket, HeadBucket, DeleteBucket, ListObjects
(v1 and v2, with ``Prefix``/``Delimiter`` and paging via ``MaxKeys``,
``Marker``/``StartAfter``/``ContinuationToken`` - ``IsTruncated``,
``NextMarker`` and ``NextContinuationToken`` mark the next page),
HeadObject and GetObject
(both honouring the ``Range`` and the ``If-Match``/``If-None-Match``
conditional headers), PutObject, CopyObject, DeleteObjects, DeleteObject
and the multipart upload operations (``CreateMultipartUpload``,
``UploadPart``, ``UploadPartCopy``, ``ListParts``, ``ListMultipartUploads``,
``CompleteMultipartUpload``, ``AbortMultipartUpload``). CopyObject is a
``PutObject`` that carries the ``x-amz-copy-source`` header; it copies the
source object's bytes to the destination, giving the new object a fresh
``LastModified``.  ``UploadPartCopy`` is an ``UploadPart`` (a ``PutObject``
with the ``uploadId`` query parameter) carrying the same header: the source
object's bytes are stored as the part, and the destination object only
materialises when the upload completes.  DeleteObjects
is the ``?delete=`` batch endpoint: it removes several keys in one request,
reporting each as ``Deleted``.  On a ``PutObject`` the
``If-Match``/``If-None-Match`` headers guard the write instead: any failed
precondition aborts it with 412 ``PreconditionFailed`` (``If-None-Match: *``
is the usual create-only-if-absent guard).  Multipart uploads ride on the
same routes: a request is a multipart call when it carries the ``uploadId``
(or ``uploads``) query parameter - ``UploadPart`` is the PUT, ``ListParts``
the GET and ``AbortMultipartUpload`` the DELETE that would otherwise be the
single-part call, and ``CreateMultipartUpload``/``CompleteMultipartUpload``
are POSTs.  ``ListMultipartUploads`` is the bucket-level ``GET`` that
instead carries the ``uploads`` query parameter; it pages like a listing
(``max-uploads``, ``key-marker``/``upload-id-marker``,
``IsTruncated``/``NextKeyMarker``/``NextUploadIdMarker``) and is the
API's only view of in-flight uploads.  In-flight parts live under the store
root's ``uploads/``
directory (see ``aws/service/s3.py``), outside the index, so listings
never see them.

User-defined metadata (``x-amz-meta-*`` headers) is persisted per object
(the index's JSON ``metadata`` column) and returned by ``GetObject``,
``HeadObject`` and ``CopyObject``.  ``CopyObject`` honours the
``x-amz-metadata-directive`` header (``COPY`` keeps the source object's
metadata, ``REPLACE`` uses the request's own headers - an empty set clears
it).  A multipart upload takes its metadata from the
``CreateMultipartUpload`` request, like S3.

Every request reads the index and the content files it names - no cache,
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
from aws.service.s3 import MAX_PART_NUMBER, S3Store

S3_NS = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'

router = APIRouter()

# The parquet-backed store; tests swap this out for an isolated temporary store.
store = S3Store(DATA_DIR)


def _iso_z(dt: datetime) -> str:
    """A datetime in S3's ISO-8601 UTC form (millisecond precision)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _content(key: str, m: dict) -> str:
    iso = _iso_z(m["last_modified"])
    return (f"<Contents><Key>{escape(key)}</Key><LastModified>{iso}</LastModified>"
            f"<ETag>&quot;{m['etag']}&quot;</ETag><Size>{m['size']}</Size>"
            "<StorageClass>STANDARD</StorageClass></Contents>")


def _list_v2_xml(name: str, prefix: str, objects: list, prefixes: list,
                 max_keys: int, truncated: bool, token: str | None,
                 next_token: str | None) -> str:
    parts = [f"<ListBucketResult {S3_NS}><Name>{escape(name)}</Name><Prefix>{escape(prefix)}</Prefix>",
             f"<KeyCount>{len(objects) + len(prefixes)}</KeyCount><MaxKeys>{max_keys}</MaxKeys>",
             f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>"]
    if token:
        parts.append(f"<ContinuationToken>{escape(token)}</ContinuationToken>")
    if next_token:
        parts.append(f"<NextContinuationToken>{escape(next_token)}</NextContinuationToken>")
    parts += [f"<CommonPrefixes><Prefix>{escape(p)}</Prefix></CommonPrefixes>" for p in prefixes]
    parts += [_content(k, m) for k, m in objects]
    parts.append("</ListBucketResult>")
    return "".join(parts)


def _list_v1_xml(name: str, prefix: str, objects: list, prefixes: list,
                 max_keys: int, marker: str, truncated: bool,
                 next_marker: str | None) -> str:
    parts = [f"<ListBucketResult {S3_NS}><Name>{escape(name)}</Name><Prefix>{escape(prefix)}</Prefix>",
             f"<Marker>{escape(marker)}</Marker><MaxKeys>{max_keys}</MaxKeys>",
             f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>"]
    if next_marker:
        parts.append(f"<NextMarker>{escape(next_marker)}</NextMarker>")
    parts += [f"<CommonPrefixes><Prefix>{escape(p)}</Prefix></CommonPrefixes>" for p in prefixes]
    parts += [_content(k, m) for k, m in objects]
    parts.append("</ListBucketResult>")
    return "".join(parts)


def _uploads_xml(bucket: str, key_marker: str, upload_id_marker: str,
                 max_uploads: int, truncated: bool, next_key: str | None,
                 next_upload_id: str | None, prefixes: list, uploads: list) -> str:
    parts = [f"<ListMultipartUploadsResult {S3_NS}><Bucket>{escape(bucket)}</Bucket>",
             f"<KeyMarker>{escape(key_marker)}</KeyMarker>",
             f"<UploadIdMarker>{escape(upload_id_marker)}</UploadIdMarker>",
             f"<MaxUploads>{max_uploads}</MaxUploads>",
             f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>"]
    if next_key is not None:
        parts.append(f"<NextKeyMarker>{escape(next_key)}</NextKeyMarker>")
        parts.append(f"<NextUploadIdMarker>{escape(next_upload_id)}</NextUploadIdMarker>")
    parts += [f"<CommonPrefixes><Prefix>{escape(p)}</Prefix></CommonPrefixes>" for p in prefixes]
    parts += [
        f"<Upload><Key>{escape(key)}</Key><UploadId>{escape(upload_id)}</UploadId>"
        "<Initiator><ID>local</ID><DisplayName>local</DisplayName></Initiator>"
        "<Owner><ID>local</ID><DisplayName>local</DisplayName></Owner>"
        "<StorageClass>STANDARD</StorageClass>"
        f"<Initiated>{_iso_z(created)}</Initiated></Upload>"
        for key, upload_id, created in uploads
    ]
    parts.append("</ListMultipartUploadsResult>")
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
    if "uploads" in request.query_params:
        return await _list_multipart_uploads(request, bucket)
    prefix = request.query_params.get("prefix", "")
    delimiter = request.query_params.get("delimiter")
    max_keys = _parse_max_keys(request.query_params.get("max-keys"))
    if max_keys is None:
        return _error(400, "InvalidArgument",
                      "Value for max-keys must be an integer greater than 0.")
    if request.query_params.get("list-type") == "2":
        # a continuation token is the exact resume point of a previous
        # page and wins over start-after when both are given
        token = request.query_params.get("continuation-token")
        marker = token or request.query_params.get("start-after") or None
        objects, prefixes, next_marker, truncated = store.list_objects_page(
            bucket, prefix, delimiter, marker, max_keys)
        return Response(
            _list_v2_xml(bucket, prefix, objects, prefixes, max_keys,
                         truncated, token, next_marker),
            media_type="application/xml")
    marker = request.query_params.get("marker", "")
    objects, prefixes, next_marker, truncated = store.list_objects_page(
        bucket, prefix, delimiter, marker or None, max_keys)
    return Response(
        _list_v1_xml(bucket, prefix, objects, prefixes, max_keys,
                     marker, truncated, next_marker),
        media_type="application/xml")


@router.delete("/{bucket}")
async def delete_bucket(bucket: str) -> Response:
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    if store.object_count(bucket):
        return _error(409, "BucketNotEmpty", "The bucket you tried to delete is not empty.")
    store.delete_bucket(bucket)
    return Response(status_code=204)


def _object_headers(m: dict) -> dict:
    """The response headers describing an object: etag, type, size, date
    and the object's user-defined ``x-amz-meta-*`` metadata."""
    headers = {
        "ETag": f'"{m["etag"]}"',
        "Content-Type": m["content_type"],
        "Last-Modified": format_datetime(m["last_modified"]),
        "Content-Length": str(m["size"]),
    }
    for name, value in (m.get("metadata") or {}).items():
        headers[f"x-amz-meta-{name}"] = value
    return headers


def _meta_headers(request: Request) -> dict:
    """The request's user-defined metadata: the ``x-amz-meta-*`` headers with
    the prefix stripped.  Header names arrive lower-cased, so keys are
    stored exactly as S3 stores them."""
    prefix = "x-amz-meta-"
    return {
        name.removeprefix(prefix): value
        for name, value in request.headers.items()
        if name.startswith(prefix)
    }


def _parse_max_keys(raw: str | None) -> int | None:
    """The requested page size (``max-keys``): S3's default of 1000 when
    absent, clamped to 1000 when larger, or ``None`` when not a positive
    integer."""
    if raw is None:
        return 1000
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < 1:
        return None
    return min(value, 1000)


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


def _copy_object(bucket: str, key: str, source: str,
                 metadata: dict | None = None) -> Response:
    """CopyObject: copy the source object's bytes to ``{bucket}/{key}``.

    ``metadata`` None means the COPY directive (keep the source object's
    user-defined metadata); a dict (possibly empty) means REPLACE.
    """
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
    m = store.copy_object(src_bucket, src_key, bucket, key, metadata)
    body = (f"<CopyObjectResult {S3_NS}><ETag>&quot;{m['etag']}&quot;</ETag>"
            f"<LastModified>{_iso_z(m['last_modified'])}</LastModified></CopyObjectResult>")
    headers = {
        "ETag": f'"{m["etag"]}"',
        "Last-Modified": format_datetime(m["last_modified"]),
    }
    for name, value in (m.get("metadata") or {}).items():
        headers[f"x-amz-meta-{name}"] = value
    return Response(
        body,
        status_code=200,
        headers=headers,
        media_type="application/xml",
    )


@router.put("/{bucket}/{key:path}")
async def put_object(request: Request, bucket: str, key: str) -> Response:
    # an uploadId makes this an UploadPart (or an UploadPartCopy carrying
    # x-amz-copy-source) and must be caught before the copy check below,
    # which would otherwise treat it as a CopyObject onto the key
    upload_id = request.query_params.get("uploadId")
    if upload_id:
        return await _upload_part(request, bucket, key, upload_id)
    copy_source = request.headers.get("x-amz-copy-source")
    if copy_source is not None:
        directive = (request.headers.get("x-amz-metadata-directive") or "").upper()
        return _copy_object(
            bucket, key, copy_source,
            _meta_headers(request) if directive == "REPLACE" else None,
        )
    # read the body up front: an unread body would desync a keep-alive
    # connection if an error is returned before the write
    data = await request.body()
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    existing = store.object_meta(bucket, key)
    pre = _put_precondition_response(request, existing["etag"] if existing is not None else None)
    if pre is not None:
        return pre
    m = store.put_object(bucket, key, data, _meta_headers(request))
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
    upload_id = request.query_params.get("uploadId")
    if upload_id:
        return _list_parts(bucket, key, upload_id)
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
async def delete_object(request: Request, bucket: str, key: str) -> Response:
    upload_id = request.query_params.get("uploadId")
    if upload_id:
        return _abort_upload(bucket, key, upload_id)
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    store.delete_object(bucket, key)
    return Response(status_code=204)


# --- multipart uploads ---
# These ride on the object routes: a request is a multipart call when it
# carries the ``uploadId`` (or ``uploads``) query parameter, which is all
# botocore's rest-xml protocol uses to tell them apart.


def _initiate_xml(bucket: str, key: str, upload_id: str) -> str:
    return (f"<InitiateMultipartUploadResult {S3_NS}><Bucket>{escape(bucket)}</Bucket>"
            f"<Key>{escape(key)}</Key><UploadId>{escape(upload_id)}</UploadId>"
            f"</InitiateMultipartUploadResult>")


def _complete_xml(bucket: str, key: str, m: dict) -> str:
    return (f"<CompleteMultipartUploadResult {S3_NS}>"
            f"<Location>/{escape(bucket)}/{escape(key)}</Location>"
            f"<Bucket>{escape(bucket)}</Bucket><Key>{escape(key)}</Key>"
            f"<ETag>&quot;{m['etag']}&quot;</ETag>"
            f"<LastModified>{_iso_z(m['last_modified'])}</LastModified>"
            f"</CompleteMultipartUploadResult>")


def _list_parts_xml(bucket: str, key: str, upload_id: str, created: datetime,
                    parts: list[tuple[int, dict]]) -> str:
    # like _list_v2_xml, list items are direct children under their
    # locationName (``Part``) - botocore's rest-xml parser expects no wrapper
    part_xml = "".join(
        f"<Part><PartNumber>{n}</PartNumber>"
        f"<LastModified>{_iso_z(m['last_modified'])}</LastModified>"
        f"<ETag>&quot;{m['etag']}&quot;</ETag><Size>{m['size']}</Size>"
        f"<StorageClass>STANDARD</StorageClass></Part>"
        for n, m in parts
    )
    return (f"<ListPartsResult {S3_NS}><Bucket>{escape(bucket)}</Bucket>"
            f"<Key>{escape(key)}</Key><UploadId>{escape(upload_id)}</UploadId>"
            f"<MaxParts>1000</MaxParts><IsTruncated>false</IsTruncated>"
            f"<Initiated>{_iso_z(created)}</Initiated>{part_xml}"
            f"</ListPartsResult>")


def _parse_complete_body(body: bytes) -> list[tuple[int, str]] | None:
    """Parse a ``CompleteMultipartUpload`` body into ``[(part_number, etag)]``.

    The body is ``<CompleteMultipartUpload><Part><PartNumber>…</PartNumber>
    <ETag>…</ETag></Part>…</CompleteMultipartUpload>`` (namespaced).
    Returns None when the body is not well-formed XML or a part names no
    number and ETag.
    """
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    parts: list[tuple[int, str]] = []
    for el in root.iter():
        if _local(el.tag) != "Part":
            continue
        number, etag = "", ""
        for child in el:
            name = _local(child.tag)
            if name == "PartNumber":
                number = (child.text or "").strip()
            elif name == "ETag":
                etag = (child.text or "").strip().strip('"')
        if not number or not etag:
            return None
        try:
            parts.append((int(number), etag))
        except ValueError:
            return None
    return parts


async def _upload_part(request: Request, bucket: str, key: str,
                       upload_id: str) -> Response:
    """UploadPart, or UploadPartCopy when the request carries
    ``x-amz-copy-source``: store one part of an in-flight upload
    (``?uploadId=``), taking its bytes from the body or from the source
    object."""
    # read the body up front: an unread body would desync a keep-alive
    # connection if an error is returned before the write (it is empty for
    # UploadPartCopy - the bytes come from the source object)
    data = await request.body()
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    try:
        number = int(request.query_params.get("partNumber", ""))
    except ValueError:
        return _error(400, "InvalidArgument", "The partNumber query parameter must be an integer.")
    if not 1 <= number <= MAX_PART_NUMBER:
        return _error(400, "InvalidArgument", "The partNumber query parameter must be between 1 and 10000.")
    copy_source = request.headers.get("x-amz-copy-source")
    if copy_source is not None:
        source = _parse_copy_source(copy_source)
        if source is None:
            return _error(400, "InvalidArgument", "The x-amz-copy-source header is malformed.")
        src_bucket, src_key = source
        if not store.bucket_exists(src_bucket):
            return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
        if store.object_meta(src_bucket, src_key) is None:
            return _error(404, "NoSuchKey", "The specified key does not exist.")
        data = store.content_path(src_bucket, src_key).read_bytes()
    part = store.upload_part(bucket, key, upload_id, number, data)
    if part is None:
        return _error(404, "NoSuchUpload", "The specified upload does not exist.")
    headers = {
        "ETag": f'"{part["etag"]}"',
        "Last-Modified": format_datetime(part["last_modified"]),
    }
    if copy_source is not None:
        # botocore reads UploadPartCopy's ETag/LastModified from the
        # CopyPartResult body, not from the headers (unlike UploadPart)
        return Response(
            f'<CopyPartResult {S3_NS}><ETag>&quot;{part["etag"]}&quot;</ETag>'
            f"<LastModified>{_iso_z(part['last_modified'])}</LastModified></CopyPartResult>",
            status_code=200,
            headers=headers,
            media_type="application/xml",
        )
    return Response(status_code=200, headers=headers)


def _list_parts(bucket: str, key: str, upload_id: str) -> Response:
    """ListParts: the parts of an in-flight upload (``?uploadId=``)."""
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    upload = store.list_parts(bucket, key, upload_id)
    if upload is None:
        return _error(404, "NoSuchUpload", "The specified upload does not exist.")
    created, parts = upload
    return Response(_list_parts_xml(bucket, key, upload_id, created, parts),
                    media_type="application/xml")


def _abort_upload(bucket: str, key: str, upload_id: str) -> Response:
    """AbortMultipartUpload: drop an in-flight upload (``?uploadId=``)."""
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
    if not store.abort_multipart_upload(bucket, key, upload_id):
        return _error(404, "NoSuchUpload", "The specified upload does not exist.")
    return Response(status_code=204)


async def _list_multipart_uploads(request: Request, bucket: str) -> Response:
    """ListMultipartUploads: the bucket's in-flight uploads
    (``GET /{bucket}?uploads``), paged like a listing via
    ``max-uploads``/``key-marker``/``upload-id-marker``."""
    prefix = request.query_params.get("prefix", "")
    delimiter = request.query_params.get("delimiter")
    max_uploads = _parse_max_keys(request.query_params.get("max-uploads"))
    if max_uploads is None:
        return _error(400, "InvalidArgument",
                      "Value for max-uploads must be an integer greater than 0.")
    key_marker = request.query_params.get("key-marker")
    upload_id_marker = request.query_params.get("upload-id-marker")
    uploads, prefixes, next_key, next_upload_id, truncated = store.list_multipart_uploads(
        bucket, prefix, delimiter, key_marker, upload_id_marker, max_uploads)
    return Response(
        _uploads_xml(bucket, key_marker or "", upload_id_marker or "", max_uploads,
                     truncated, next_key, next_upload_id, prefixes, uploads),
        media_type="application/xml")


@router.post("/{bucket}/{key:path}")
async def multipart(request: Request, bucket: str, key: str) -> Response:
    """Multipart uploads: ``?uploads`` starts one, ``?uploadId=`` completes it."""
    if "uploads" in request.query_params:
        if not store.bucket_exists(bucket):
            return _error(404, "NoSuchBucket", "The specified bucket does not exist.")
        upload_id, _created = store.create_multipart_upload(bucket, key,
                                                            _meta_headers(request))
        return Response(_initiate_xml(bucket, key, upload_id), media_type="application/xml")

    upload_id = request.query_params.get("uploadId", "")
    if not upload_id:
        return _error(400, "InvalidRequest", "A POST on an object key expects ?uploads or ?uploadId=.")
    # read the body up front, like put_object: an unread body would desync
    # a keep-alive connection if an error is returned before the write
    body = await request.body()
    if not store.bucket_exists(bucket):
        return _error(404, "NoSuchBucket", "The specified bucket does not exist.")

    parts = _parse_complete_body(body)
    if not parts:
        return _error(400, "MalformedXML", "The XML you provided was not well-formed.")
    numbers = [n for n, _ in parts]
    if numbers != sorted(numbers) or len(set(numbers)) != len(numbers):
        return _error(400, "InvalidPartOrder", "The parts were not in ascending order of part number.")
    uploaded = store.list_parts(bucket, key, upload_id)
    if uploaded is None:
        return _error(404, "NoSuchUpload", "The specified upload does not exist.")
    stored = dict(uploaded[1])
    for number, etag in parts:
        part = stored.get(number)
        if part is None or part["etag"] != etag:
            return _error(400, "InvalidPart",
                          "One or more of the specified parts could not be found; the part's ETag may have changed.")
    meta = store.complete_multipart_upload(bucket, key, upload_id, numbers)
    if meta is None:  # the upload vanished between the checks above
        return _error(404, "NoSuchUpload", "The specified upload does not exist.")
    return Response(_complete_xml(bucket, key, meta), media_type="application/xml")
