"""S3-compatible REST routes backed by a local data directory.

Implements just enough of the S3 REST protocol for a boto3 client to
manage, store and retrieve objects.  Buckets are directories under
``DATA_DIR``; a bucket's objects are the files beneath it.  Supported
calls: ListBuckets, CreateBucket, HeadBucket, DeleteBucket, ListObjects
(v1 and v2, with ``Prefix``/``Delimiter``), HeadObject, GetObject,
PutObject and DeleteObject.

Everything is read from, and written to, the filesystem on every
request - no state, no cache.  Request signatures are accepted but
not verified.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
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


@router.put("/{bucket}/{key:path}")
async def put_object(request: Request, bucket: str, key: str) -> Response:
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    data = await request.body()
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
async def head_object(bucket: str, key: str) -> Response:
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    if not p.is_file():
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    return Response(status_code=200, headers=_object_headers(_meta(p)))


@router.get("/{bucket}/{key:path}")
async def get_object(bucket: str, key: str) -> Response:
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    if not p.is_file():
        return _error(404, "NoSuchKey", "The specified key does not exist.")
    m = _meta(p)
    return Response(p.read_bytes(), headers=_object_headers(m), media_type=m["type"])


@router.delete("/{bucket}/{key:path}")
async def delete_object(bucket: str, key: str) -> Response:
    p = _object_path(bucket, key)
    if isinstance(p, Response):
        return p
    if not p.is_dir():
        p.unlink(missing_ok=True)  # idempotent, like S3
    return Response(status_code=204)
