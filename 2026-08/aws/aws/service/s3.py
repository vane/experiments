"""CSV-backed S3 store with boto3-compatible semantics.

All metadata lives in a single CSV file (``s3.csv`` under the store's
root directory): one row per bucket and one row per object, recording
last-modified, size, ETag and content type.  Object contents live as
files under the root's ``data/`` subdirectory - one flat file per
object, named by the percent-encoded key, so a key can never escape
the store or collide with a directory.

The CSV is the index: listings are computed from it (no filesystem
walking), and every mutation rewrites it atomically (write to a temp
file, then ``os.replace``).
"""

from __future__ import annotations

import csv
import hashlib
import mimetypes
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

# CSV columns, in file order.
_COLUMNS = ["kind", "bucket", "key", "last_modified", "size", "etag", "content_type"]

# Timestamp format; the sub-second part is trimmed to milliseconds.
_TS = "%Y-%m-%dT%H:%M:%S.%f"


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    """A datetime in ISO-8601 form with millisecond precision."""
    return dt.strftime(_TS)[:-3]


def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value, _TS).replace(tzinfo=UTC)


def _guess_type(key: str) -> str:
    """The content type to record for ``key`` (guessed from the last segment)."""
    return mimetypes.guess_type(key.rsplit("/", 1)[-1])[0] or "application/octet-stream"


def _write_atomic(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` via a temp file so a crash mid-write
    cannot leave a truncated object behind."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


class S3Store:
    """Buckets and objects backed by a CSV index and a content directory.

    ``root`` is the store's data directory: it holds ``s3.csv`` and the
    ``data/`` content subdirectory (``root/data/<bucket>/<key>``).
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.csv_path = self.root / "s3.csv"
        self.content_dir = self.root / "data"
        self.buckets: dict[str, datetime] = {}
        self.objects: dict[tuple[str, str], dict] = {}
        self._load()

    # --- persistence ---

    def _load(self) -> None:
        if not self.csv_path.is_file():
            return
        with self.csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["kind"] == "bucket":
                    self.buckets[row["bucket"]] = _parse_ts(row["last_modified"])
                else:
                    self.objects[(row["bucket"], row["key"])] = {
                        "last_modified": _parse_ts(row["last_modified"]),
                        "size": int(row["size"]),
                        "etag": row["etag"],
                        "content_type": row["content_type"],
                    }

    def _save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.csv_path.with_name(self.csv_path.name + ".tmp")
        with tmp.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_COLUMNS)
            for name, created in sorted(self.buckets.items()):
                writer.writerow(["bucket", name, "", _iso(created), "", "", ""])
            for (bucket, key), meta in sorted(self.objects.items()):
                writer.writerow([
                    "object", bucket, key, _iso(meta["last_modified"]),
                    str(meta["size"]), meta["etag"], meta["content_type"],
                ])
        os.replace(tmp, self.csv_path)

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
        """Delete an existing bucket and its content directory."""
        del self.buckets[name]
        shutil.rmtree(self.content_dir / name, ignore_errors=True)
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

    def put_object(self, bucket: str, key: str, data: bytes) -> dict:
        """Write an object's contents and record its metadata row."""
        path = self.content_path(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, data)
        meta = {
            "last_modified": _now(),
            "size": len(data),
            "etag": hashlib.md5(data).hexdigest(),
            "content_type": _guess_type(key),
        }
        self.objects[(bucket, key)] = meta
        self._save()
        return meta

    def copy_object(self, src_bucket: str, src_key: str, bucket: str, key: str) -> dict:
        """Copy one object's contents to another key with a fresh LastModified."""
        data = self.content_path(src_bucket, src_key).read_bytes()
        meta = {
            "last_modified": _now(),
            "size": len(data),
            "etag": hashlib.md5(data).hexdigest(),
            "content_type": _guess_type(key),
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
        return sorted(objects), sorted(prefixes)
