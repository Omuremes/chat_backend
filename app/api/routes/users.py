from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.repositories import user_repository
from app.schemas import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    return user_repository.update_profile(current_user, payload.display_name, payload.avatar_url)


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: UserRead = Depends(get_current_user),
) -> list[UserRead]:
    return user_repository.list_except_user(current_user)


@router.get("/search", response_model=list[UserRead])
def search_users(
    q: str = Query(min_length=1, max_length=120),
    current_user: UserRead = Depends(get_current_user),
) -> list[UserRead]:
    return user_repository.search_except_user(current_user, q)
