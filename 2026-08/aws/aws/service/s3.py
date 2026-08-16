"""Parquet-backed S3 store with boto3-compatible semantics.

All metadata lives in a single parquet file (``s3.parquet`` under the
store's root directory): one row per bucket and one row per object,
recording last-modified (a UTC timestamp column), size, ETag, content
type and the object's user-defined metadata (``x-amz-meta-*``) as a JSON
object column.  Object contents live as files under the root's ``data/``
subdirectory - one flat file per object, named by the percent-encoded
key, so a key can never escape the store or collide with a directory.

The parquet file is the index: listings are computed from it (no
filesystem walking), and every mutation rewrites it atomically (write
to a temp file, then ``os.replace``).

In-flight multipart uploads live outside the index, under the root's
``uploads/`` subdirectory: one directory per upload holding its part
files plus a single ``upload.json`` record (also rewritten atomically).
A part is not an object, so listings never see it; completing an upload
writes the assembled object into the store like a plain put.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import pyarrow as pa
import pyarrow.parquet as pq

# The index's schema (column order is the on-disk order).  ``metadata``
# is a JSON object encoded as a string, mirroring how values like it are
# best inspected in any parquet tooling.
_SCHEMA = pa.schema([
    pa.field("kind", pa.string()),
    pa.field("bucket", pa.string()),
    pa.field("key", pa.string()),
    pa.field("last_modified", pa.timestamp("us", tz="UTC")),
    pa.field("size", pa.int64()),
    pa.field("etag", pa.string()),
    pa.field("content_type", pa.string()),
    pa.field("metadata", pa.string()),
])

# Timestamp format; the sub-second part is trimmed to milliseconds.
_TS = "%Y-%m-%dT%H:%M:%S.%f"

# S3 caps a multipart upload at 10000 parts, numbered 1..10000.
MAX_PART_NUMBER = 10000


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    """A datetime in ISO-8601 form with millisecond precision."""
    return dt.strftime(_TS)[:-3]


def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value, _TS).replace(tzinfo=UTC)


def _utc(dt: datetime) -> datetime:
    """A timestamp read from the index, normalised to UTC (a naive value,
    e.g. from an index written by another tool, is taken as UTC)."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def _json_dict(value: str | None) -> dict:
    """Parse the index's JSON ``metadata`` column (absent, empty or
    malformed -> empty)."""
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _guess_type(key: str) -> str:
    """The content type to record for ``key`` (guessed from the last segment)."""
    return mimetypes.guess_type(key.rsplit("/", 1)[-1])[0] or "application/octet-stream"


def _write_atomic(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` via a temp file so a crash mid-write
    cannot leave a truncated object behind."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _multipart_etag(part_etags: list[str]) -> str:
    """The ETag S3 reports for a multipart object: the hex MD5 of the
    parts' binary MD5 digests, suffixed with ``-<part count>``."""
    digest = hashlib.md5()
    for etag in part_etags:
        digest.update(bytes.fromhex(etag))
    return f"{digest.hexdigest()}-{len(part_etags)}"


class S3Store:
    """Buckets and objects backed by a parquet index and a content directory.

    ``root`` is the store's data directory: it holds ``s3.parquet`` and the
    ``data/`` content subdirectory (``root/data/<bucket>/<key>``).
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.index_path = self.root / "s3.parquet"
        self.content_dir = self.root / "data"
        self.buckets: dict[str, datetime] = {}
        self.objects: dict[tuple[str, str], dict] = {}
        self._load()

    # --- persistence ---

    def _load(self) -> None:
        if not self.index_path.is_file():
            return
        rows = pq.read_table(self.index_path).to_pydict()
        for kind, bucket, key, last_modified, size, etag, content_type, metadata in zip(
            rows["kind"], rows["bucket"], rows["key"], rows["last_modified"],
            rows["size"], rows["etag"], rows["content_type"], rows["metadata"],
        ):
            if kind == "bucket":
                self.buckets[bucket] = _utc(last_modified)
            else:
                self.objects[(bucket, key)] = {
                    "last_modified": _utc(last_modified),
                    "size": size,
                    "etag": etag,
                    "content_type": content_type,
                    "metadata": _json_dict(metadata),
                }

    def _save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        buckets = sorted(self.buckets.items())
        objects = sorted(self.objects.items())
        table = pa.Table.from_pydict({
            "kind": ["bucket"] * len(buckets) + ["object"] * len(objects),
            "bucket": [name for name, _ in buckets]
                      + [bk for (bk, _), _ in objects],
            "key": [""] * len(buckets) + [key for (_, key), _ in objects],
            "last_modified": [created for _, created in buckets]
                             + [m["last_modified"] for _, m in objects],
            "size": [0] * len(buckets) + [m["size"] for _, m in objects],
            "etag": [""] * len(buckets) + [m["etag"] for _, m in objects],
            "content_type": [""] * len(buckets)
                            + [m["content_type"] for _, m in objects],
            "metadata": [""] * len(buckets)
                        + [json.dumps(m.get("metadata") or {}) for _, m in objects],
        }, schema=_SCHEMA)
        tmp = self.index_path.with_name(self.index_path.name + ".tmp")
        pq.write_table(table, tmp)
        os.replace(tmp, self.index_path)

    # --- buckets ---

    def _valid_bucket_name(self, name: str) -> bool:
        """A bucket name must stay inside the content directory."""
        p = (self.content_dir / name).resolve()
        try:
            p.relative_to(self.content_dir)
        except ValueError:
            return False
        return True

    def create_bucket(self, name: str) -> bool:
        """Create a bucket (idempotent).  Returns False when the name is invalid."""
        if not self._valid_bucket_name(name):
            return False
        if name not in self.buckets:
            self.buckets[name] = _now()
            self._save()
        return True

    def bucket_exists(self, name: str) -> bool:
        return name in self.buckets

    def list_buckets(self) -> list[tuple[str, datetime]]:
        return sorted(self.buckets.items())

    def delete_bucket(self, name: str) -> None:
        """Delete an existing bucket, its content directory and any
        in-flight uploads."""
        del self.buckets[name]
        shutil.rmtree(self.content_dir / name, ignore_errors=True)
        shutil.rmtree(self.root / "uploads" / name, ignore_errors=True)
        self._save()

    def object_count(self, bucket: str) -> int:
        return sum(1 for b, _ in self.objects if b == bucket)

    # --- objects ---

    def content_path(self, bucket: str, key: str) -> Path:
        """The content file for a key: a flat, percent-encoded name under the
        bucket's content directory (never a nested path, so a key can never
        escape the store)."""
        return self.content_dir / bucket / quote(key, safe="")

    def object_meta(self, bucket: str, key: str) -> dict | None:
        return self.objects.get((bucket, key))

    def put_object(self, bucket: str, key: str, data: bytes,
                   metadata: dict | None = None) -> dict:
        """Write an object's contents and record its metadata row.

        ``metadata`` is the object's user-defined (``x-amz-meta-*``)
        metadata; None records none.
        """
        path = self.content_path(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, data)
        meta = {
            "last_modified": _now(),
            "size": len(data),
            "etag": hashlib.md5(data).hexdigest(),
            "content_type": _guess_type(key),
            "metadata": dict(metadata or {}),
        }
        self.objects[(bucket, key)] = meta
        self._save()
        return meta

    def copy_object(self, src_bucket: str, src_key: str, bucket: str, key: str,
                    metadata: dict | None = None) -> dict:
        """Copy one object's contents to another key with a fresh
        LastModified.

        ``metadata`` None means COPY: the source object's user-defined
        metadata is kept.  A dict (possibly empty) means REPLACE: the
        destination gets exactly that metadata.
        """
        data = self.content_path(src_bucket, src_key).read_bytes()
        if metadata is None:
            source = self.object_meta(src_bucket, src_key)
            metadata = dict((source or {}).get("metadata") or {})
        meta = {
            "last_modified": _now(),
            "size": len(data),
            "etag": hashlib.md5(data).hexdigest(),
            "content_type": _guess_type(key),
            "metadata": metadata,
        }
        dest = self.content_path(bucket, key)
        if dest != self.content_path(src_bucket, src_key):
            dest.parent.mkdir(parents=True, exist_ok=True)
            _write_atomic(dest, data)
        self.objects[(bucket, key)] = meta
        self._save()
        return meta

    def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object if present (a no-op otherwise, like S3)."""
        if self.objects.pop((bucket, key), None) is not None:
            self.content_path(bucket, key).unlink(missing_ok=True)
            self._save()

    def delete_objects(self, bucket: str, keys: list[str]) -> list[str]:
        """Delete several keys at once; every key is reported as deleted."""
        removed = False
        for key in keys:
            if self.objects.pop((bucket, key), None) is not None:
                self.content_path(bucket, key).unlink(missing_ok=True)
                removed = True
        if removed:
            self._save()
        return list(keys)

    def list_objects(
        self, bucket: str, prefix: str, delimiter: str | None
    ) -> tuple[list[tuple[str, dict]], list[str]]:
        """The bucket's objects (key, meta) and common prefixes."""
        objects, prefixes, _, _ = self.list_objects_page(
            bucket, prefix, delimiter, None, len(self.objects)
        )
        return objects, prefixes

    def list_objects_page(
        self, bucket: str, prefix: str, delimiter: str | None,
        marker: str | None, max_keys: int,
    ) -> tuple[list[tuple[str, dict]], list[str], str | None, bool]:
        """One page of the bucket's listing, S3-style.

        Objects and common prefixes form a single stream sorted by key
        (S3 interleaves them in the response); ``marker`` starts the page
        just after that key, and ``max_keys`` bounds how many entries the
        page holds, objects and prefixes alike.  Returns the page's
        objects and prefixes, the marker that fetches the next page
        (``None`` when the page is the last one), and whether entries
        follow the page.
        """
        objects: list[tuple[str, dict]] = []
        prefixes: set[str] = set()
        for (b, key), meta in self.objects.items():
            if b != bucket or not key.startswith(prefix):
                continue
            rest = key[len(prefix):]
            if delimiter and delimiter in rest:
                prefixes.add(prefix + rest.split(delimiter, 1)[0] + delimiter)
            else:
                objects.append((key, meta))

        entries: list[tuple[str, dict | None]] = [(k, m) for k, m in objects]
        entries += [(p, None) for p in prefixes]
        entries.sort(key=lambda entry: entry[0])
        if marker is not None:
            entries = [entry for entry in entries if entry[0] > marker]
        truncated = len(entries) > max_keys
        page = entries[:max_keys]
        next_marker = page[-1][0] if truncated else None
        return (
            [(k, m) for k, m in page if m is not None],
            [k for k, m in page if m is None],
            next_marker,
            truncated,
        )

    # --- multipart uploads ---
    #
    # In-flight uploads live outside the index (and the content directory):
    # one directory per upload under the root's ``uploads/`` subdirectory,
    # holding the part files plus a single ``upload.json`` record that is
    # rewritten atomically on every part, so a crash never leaves a torn
    # upload behind.  Completing an upload writes the assembled object
    # into the store like a plain put and drops the directory.

    def upload_dir(self, bucket: str, upload_id: str) -> Path:
        """The directory holding an in-flight upload's parts and record."""
        return self.root / "uploads" / bucket / upload_id

    def _upload_path(self, bucket: str, upload_id: str) -> Path:
        return self.upload_dir(bucket, upload_id) / "upload.json"

    def _load_upload(self, bucket: str, upload_id: str) -> dict | None:
        path = self._upload_path(bucket, upload_id)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _save_upload(self, bucket: str, upload_id: str, meta: dict) -> None:
        directory = self.upload_dir(bucket, upload_id)
        directory.mkdir(parents=True, exist_ok=True)
        _write_atomic(
            self._upload_path(bucket, upload_id), json.dumps(meta).encode("utf-8")
        )

    def _upload_for(self, bucket: str, key: str, upload_id: str) -> dict | None:
        """The upload's record, or None when it is unknown or was started for
        another key (S3 addresses every part by the upload's own key)."""
        meta = self._load_upload(bucket, upload_id)
        if meta is None or meta.get("key") != key:
            return None
        return meta

    def create_multipart_upload(self, bucket: str, key: str,
                                metadata: dict | None = None) -> tuple[str, datetime]:
        """Start a multipart upload; return ``(upload_id, created)``.

        ``metadata`` is the user-defined metadata the final object gets when
        the upload completes (S3 takes it from the create request; there is
        no metadata parameter on the complete call).
        """
        created = _now()
        upload_id = uuid.uuid4().hex
        self._save_upload(
            bucket, upload_id, {"key": key, "created": _iso(created),
                                "metadata": dict(metadata or {}), "parts": {}}
        )
        return upload_id, created

    def upload_part(
        self, bucket: str, key: str, upload_id: str, part_number: int, data: bytes
    ) -> dict | None:
        """Store one part (overwriting an earlier upload of the same
        number); None when the upload is unknown."""
        meta = self._upload_for(bucket, key, upload_id)
        if meta is None:
            return None
        last_modified = _now()
        part = {"size": len(data), "etag": hashlib.md5(data).hexdigest()}
        _write_atomic(self.upload_dir(bucket, upload_id) / f"part-{part_number}", data)
        meta["parts"][str(part_number)] = {**part, "last_modified": _iso(last_modified)}
        self._save_upload(bucket, upload_id, meta)
        return {**part, "last_modified": last_modified}

    def list_parts(
        self, bucket: str, key: str, upload_id: str
    ) -> tuple[datetime, list[tuple[int, dict]]] | None:
        """The upload's ``(created, parts)`` in ascending part number, or
        None when the upload is unknown."""
        meta = self._upload_for(bucket, key, upload_id)
        if meta is None:
            return None
        parts = sorted(
            (
                int(n),
                {**m, "last_modified": _parse_ts(m["last_modified"])},
            )
            for n, m in meta["parts"].items()
        )
        return _parse_ts(meta["created"]), parts

    def complete_multipart_upload(
        self, bucket: str, key: str, upload_id: str, part_numbers: list[int]
    ) -> dict | None:
        """Assemble the object from ``part_numbers`` (already validated as
        ascending and present by the caller), drop the upload, and return
        the object's metadata; None when the upload vanished in between."""
        meta = self._upload_for(bucket, key, upload_id)
        if meta is None:
            return None
        stored = meta["parts"]
        data = b"".join(
            (self.upload_dir(bucket, upload_id) / f"part-{n}").read_bytes()
            for n in part_numbers
        )
        object_meta = {
            "last_modified": _now(),
            "size": len(data),
            "etag": _multipart_etag([stored[str(n)]["etag"] for n in part_numbers]),
            "content_type": _guess_type(key),
            "metadata": meta.get("metadata") or {},
        }
        path = self.content_path(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, data)
        self.objects[(bucket, key)] = object_meta
        self._save()
        shutil.rmtree(self.upload_dir(bucket, upload_id), ignore_errors=True)
        return object_meta

    def abort_multipart_upload(self, bucket: str, key: str, upload_id: str) -> bool:
        """Remove an in-flight upload; False when it is unknown."""
        if self._upload_for(bucket, key, upload_id) is None:
            return False
        shutil.rmtree(self.upload_dir(bucket, upload_id), ignore_errors=True)
        return True

    def list_multipart_uploads(
        self, bucket: str, prefix: str, delimiter: str | None,
        key_marker: str | None, upload_id_marker: str | None, max_keys: int,
    ) -> tuple[list[tuple[str, str, datetime]], list[str], str | None, str | None, bool]:
        """One page of the bucket's in-flight uploads, S3-style.

        Uploads are sorted by ``(key, upload_id)``; the marker pair starts
        the page just after ``(key_marker, upload_id_marker)`` (an empty
        upload id sorts before any real one, which is how a common prefix
        pages relative to an upload of the same key), and ``max_keys``
        bounds how many entries the page holds, uploads and prefixes
        alike.  Returns the page's uploads ``(key, upload_id, created)``
        and common prefixes, the next page's markers (``None`` when the
        page is the last one), and whether entries follow the page.
        """
        uploads: list[tuple[str, str, datetime]] = []
        bucket_uploads = self.root / "uploads" / bucket
        if bucket_uploads.is_dir():
            for upload_dir in bucket_uploads.iterdir():
                if not upload_dir.is_dir():
                    continue
                meta = self._load_upload(bucket, upload_dir.name)
                if meta is None or not meta.get("key", "").startswith(prefix):
                    continue
                uploads.append(
                    (meta["key"], upload_dir.name, _parse_ts(meta["created"]))
                )

        entries: list[tuple[str, str, datetime | None]] = []
        prefixes: set[str] = set()
        for key, upload_id, created in uploads:
            rest = key[len(prefix):]
            if delimiter and delimiter in rest:
                prefixes.add(prefix + rest.split(delimiter, 1)[0] + delimiter)
            else:
                entries.append((key, upload_id, created))
        entries += [(p, "", None) for p in prefixes]
        entries.sort(key=lambda entry: (entry[0], entry[1]))
        if key_marker is not None:
            marker = (key_marker, upload_id_marker or "")
            entries = [e for e in entries if (e[0], e[1]) > marker]
        truncated = len(entries) > max_keys
        page = entries[:max_keys]
        next_key, next_upload_id = (
            (page[-1][0], page[-1][1]) if truncated else (None, None)
        )
        return (
            [(k, uid, created) for k, uid, created in page if created is not None],
            [k for k, _, _ in page if _ is None],
            next_key,
            next_upload_id,
            truncated,
        )
