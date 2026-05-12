import json

import firebase_admin
from fastapi import HTTPException, status
from firebase_admin import auth, credentials
from firebase_admin.auth import GetUsersResult, UserRecord

from app.core.config import get_settings


def _build_credentials() -> credentials.Certificate:
    settings = get_settings()

    if settings.firebase_credentials_path:
        return credentials.Certificate(settings.firebase_credentials_path)

    if settings.firebase_credentials_json:
        return credentials.Certificate(json.loads(settings.firebase_credentials_json))

    if settings.firebase_project_id and settings.firebase_client_email and settings.firebase_private_key:
        private_key = settings.firebase_private_key.replace("\\n", "\n")
        return credentials.Certificate(
            {
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "private_key": private_key,
                "client_email": settings.firebase_client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )

    raise RuntimeError(
        "Firebase Admin credentials are not configured. Set FIREBASE_CREDENTIALS_PATH, "
        "FIREBASE_CREDENTIALS_JSON, or FIREBASE_PROJECT_ID/FIREBASE_CLIENT_EMAIL/FIREBASE_PRIVATE_KEY."
    )


def _initialize_firebase() -> None:
    if firebase_admin._apps:
        return

    firebase_admin.initialize_app(_build_credentials())


def verify_firebase_token(token: str) -> dict:
    try:
        _initialize_firebase()
        return auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        ) from exc


def get_auth_user(uid: str) -> UserRecord:
    try:
        _initialize_firebase()
        return auth.get_user(uid)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase user not found") from exc


def get_auth_users(uids: list[str]) -> GetUsersResult:
    try:
        _initialize_firebase()
        return auth.get_users([auth.UidIdentifier(uid) for uid in uids])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not load Firebase Auth users") from exc


def list_auth_users(max_results: int = 1000) -> list[UserRecord]:
    try:
        _initialize_firebase()
        return list(auth.list_users(max_results=max_results).iterate_all())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not load Firebase Auth users") from exc


def update_auth_user(uid: str, display_name: str | None = None, photo_url: str | None = None) -> UserRecord:
    try:
        _initialize_firebase()
        updates: dict[str, str | None] = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if photo_url is not None:
            updates["photo_url"] = photo_url
        if updates:
            auth.update_user(uid, **updates)
        return auth.get_user(uid)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not update Firebase Auth profile") from exc
