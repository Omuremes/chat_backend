from datetime import UTC, datetime

from firebase_admin.auth import UserRecord

from app.core.firebase import get_auth_user, get_auth_users, list_auth_users, update_auth_user
from app.schemas import UserRead


def _from_millis(value: int | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromtimestamp(value / 1000, UTC)


def from_record(record: UserRecord) -> UserRead:
    created_at = _from_millis(record.user_metadata.creation_timestamp) if record.user_metadata else datetime.now(UTC)
    updated_at = _from_millis(record.user_metadata.last_sign_in_timestamp) if record.user_metadata else created_at
    return UserRead(
        id=record.uid,
        firebase_uid=record.uid,
        email=record.email or f"{record.uid}@firebase.local",
        display_name=record.display_name,
        avatar_url=record.photo_url,
        created_at=created_at,
        updated_at=updated_at,
    )


def get_by_id(user_id: str) -> UserRead:
    return from_record(get_auth_user(user_id))


def get_by_ids(user_ids: set[str] | list[str]) -> dict[str, UserRead]:
    ordered_ids = list(dict.fromkeys(user_id for user_id in user_ids if user_id))
    if not ordered_ids:
        return {}

    users: dict[str, UserRead] = {}
    for index in range(0, len(ordered_ids), 100):
        result = get_auth_users(ordered_ids[index : index + 100])
        users.update({record.uid: from_record(record) for record in result.users})
    return users


def list_except_user(current_user: UserRead) -> list[UserRead]:
    return [
        from_record(record)
        for record in list_auth_users()
        if record.uid != current_user.id and record.email
    ]


def search_except_user(current_user: UserRead, query: str) -> list[UserRead]:
    needle = query.strip().lower()
    if not needle:
        return []

    users = []
    for record in list_auth_users():
        if record.uid == current_user.id or not record.email:
            continue
        haystack = f"{record.email} {record.display_name or ''}".lower()
        if needle in haystack:
            users.append(from_record(record))
        if len(users) >= 25:
            break
    return users


def update_profile(user: UserRead, display_name: str | None, avatar_url: str | None) -> UserRead:
    return from_record(update_auth_user(user.id, display_name=display_name, photo_url=avatar_url))
