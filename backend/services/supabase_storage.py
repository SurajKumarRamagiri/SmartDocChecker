"""Supabase Storage service for uploading and managing files."""
import logging
import threading
from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None
_client_lock = threading.Lock()


def _get_client() -> Client:
    """Lazy-initialize the Supabase client (thread-safe)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:  # double-checked locking
                if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
                    raise RuntimeError(
                        "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
                    )
                _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                logger.info("Supabase client initialized")
    return _client


def upload_file(
    file_bytes: bytes,
    file_path: str,
    content_type: str = "application/octet-stream",
    bucket: str | None = None,
) -> str:
    """
    Upload a file to Supabase Storage.

    Args:
        file_bytes: Raw file content.
        file_path: Path inside the bucket, e.g. "user_1/abc123.pdf".
        content_type: MIME type of the file.
        bucket: Override bucket name (defaults to settings.SUPABASE_BUCKET).

    Returns:
        The storage path of the uploaded file.
    """
    client = _get_client()
    bucket_name = bucket or settings.SUPABASE_BUCKET

    client.storage.from_(bucket_name).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )

    logger.info(f"Uploaded {file_path} to bucket '{bucket_name}'")
    return file_path


def get_public_url(file_path: str, bucket: str | None = None) -> str:
    """Get the public URL for a file in Supabase Storage."""
    client = _get_client()
    bucket_name = bucket or settings.SUPABASE_BUCKET
    res = client.storage.from_(bucket_name).get_public_url(file_path)
    return res


def get_signed_url(
    file_path: str, expires_in: int = 3600, bucket: str | None = None
) -> str:
    """Get a signed (temporary) URL for a file in Supabase Storage."""
    client = _get_client()
    bucket_name = bucket or settings.SUPABASE_BUCKET
    res = client.storage.from_(bucket_name).create_signed_url(file_path, expires_in)
    signed_url = res.get("signedURL", "")
    if not signed_url:
        raise RuntimeError(
            f"Failed to generate signed URL for '{file_path}' in bucket '{bucket_name}'"
        )
    return signed_url


def delete_file(file_path: str, bucket: str | None = None) -> None:
    """Delete a file from Supabase Storage."""
    client = _get_client()
    bucket_name = bucket or settings.SUPABASE_BUCKET
    client.storage.from_(bucket_name).remove([file_path])
    logger.info(f"Deleted {file_path} from bucket '{bucket_name}'")
