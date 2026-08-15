"""Application settings for the fs-s3 API.

DATA_DIR is the on-disk store backing the S3 routes (``aws/routes/s3.py``):
buckets are directories under it, and a bucket's objects are the files
beneath that directory.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
