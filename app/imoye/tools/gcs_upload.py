import os
from google.cloud import storage
from fastapi import UploadFile
from typing import Tuple
import uuid

from ..config import PROJECT_ID

BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

class GCSUploadError(Exception):
    pass

def upload_file_to_gcs(file: UploadFile, allowed_exts=None, max_mb=40) -> Tuple[str, str]:
    if allowed_exts is None:
        allowed_exts = ["pdf", "txt", "docx"]

    ext = file.filename.split(".")[-1].lower()
    if ext not in allowed_exts:
        raise GCSUploadError(f"File type .{ext} not allowed. Allowed: {allowed_exts}")

    file.file.seek(0, 2)
    size_mb = file.file.tell() / (1024 * 1024)
    if size_mb > max_mb:
        raise GCSUploadError(f"File size {size_mb:.2f}MB exceeds {max_mb}MB limit.")
    file.file.seek(0)

    if not BUCKET_NAME:
        raise GCSUploadError("GCS_BUCKET_NAME environment variable not set.")

    # Create a unique blob name
    blob_name = f"rag_uploads/{uuid.uuid4().hex}_{file.filename}"
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)

    blob.upload_from_file(file.file, content_type=file.content_type)

    # Do NOT call blob.make_public()
    # Construct a signed URL instead if needed

    # Use this if you want to generate a temporary signed URL (optional)
    # from datetime import timedelta
    # url = blob.generate_signed_url(expiration=timedelta(hours=1))

    # Return GCS path instead of public URL
    public_url = f"gs://{BUCKET_NAME}/{blob_name}"
    return public_url, blob_name
