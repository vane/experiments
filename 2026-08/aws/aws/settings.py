"""Application settings for the fs-s3 API.

DATA_DIR is the on-disk store backing the S3 API (``aws/service/s3.py``):
``s3.csv`` holds the bucket/object metadata and ``data/`` holds the
objects' contents (one flat percent-encoded file per object).
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
