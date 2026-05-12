from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


def _is_publishable_key(key: str) -> bool:
    return key.startswith("sb_publishable_")


def _looks_like_jwt(key: str) -> bool:
    return key.count(".") == 2


async def upload_file(file: UploadFile, folder: str, user_id: str) -> tuple[str, str]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image uploads are supported")

    safe_folder = "avatars" if folder == "avatars" else "messages"
    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    object_path = f"{safe_folder}/{user_id}/{uuid4().hex}{extension}"
    payload = await file.read()

    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    settings = get_settings()
    if _is_publishable_key(settings.supabase_service_role_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "SUPABASE_SERVICE_ROLE_KEY is set to a publishable key. "
                "Backend Storage uploads require the Supabase service_role key or sb_secret key from the same project."
            ),
        )

    upload_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}/{object_path}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "content-type": file.content_type,
        "x-upsert": "false",
    }
    if _looks_like_jwt(settings.supabase_service_role_key) or settings.supabase_service_role_key.startswith("sb_secret_"):
        headers["authorization"] = f"Bearer {settings.supabase_service_role_key}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(upload_url, content=payload, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"Could not reach Supabase Storage at {settings.supabase_url}. "
                "Check SUPABASE_URL in backend/.env and rebuild the backend container."
            ),
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Supabase Storage rejected upload: {response.text}. "
                "Use the service_role key or sb_secret key from the same Supabase project."
            ),
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase Storage upload failed: {response.text}",
        )

    public_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{settings.supabase_bucket}/{object_path}"
    return public_url, object_path
