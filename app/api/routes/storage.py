from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_user
from app.repositories import user_repository
from app.schemas import UploadResponse, UserRead
from app.services.storage_service import upload_file

router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    folder: str = Form(default="messages"),
    current_user: UserRead = Depends(get_current_user),
) -> UploadResponse:
    url, path = await upload_file(file, folder, current_user.id)
    return UploadResponse(url=url, path=path)


@router.post("/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    url, _ = await upload_file(file, "avatars", current_user.id)
    return user_repository.update_profile(current_user, display_name=None, avatar_url=url)
