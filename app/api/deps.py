from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.firebase import verify_firebase_token
from app.repositories import user_repository
from app.schemas import UserRead

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_from_token(decoded_token: dict) -> UserRead:
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase token missing uid")
    return user_repository.get_by_id(firebase_uid)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserRead:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    decoded_token = verify_firebase_token(credentials.credentials)
    return get_user_from_token(decoded_token)


def authenticate_token_for_websocket(token: str) -> UserRead:
    decoded_token = verify_firebase_token(token)
    return get_user_from_token(decoded_token)
