from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Message
from app.repositories import message_repository, user_repository
from app.schemas import UserRead
from app.services.conversation_service import require_participant


def serialize_message(message: Message, sender: UserRead | None = None, lookup_sender: bool = True) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "content": message.content,
        "image_url": message.image_url,
        "is_deleted": message.is_deleted,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
        "sender": sender if sender is not None or not lookup_sender else user_repository.get_by_id(message.sender_id),
    }


def serialize_messages(messages: list[Message]) -> list[dict]:
    users_by_id = user_repository.get_by_ids({message.sender_id for message in messages})
    return [serialize_message(message, users_by_id.get(message.sender_id), lookup_sender=False) for message in messages]


def list_messages(db: Session, conversation_id: int, user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    require_participant(db, conversation_id, user_id)
    return serialize_messages(message_repository.list_for_conversation(db, conversation_id, limit=limit, offset=offset))


def create_message(
    db: Session,
    conversation_id: int,
    sender: UserRead,
    content: str,
    image_url: str | None = None,
) -> dict:
    require_participant(db, conversation_id, sender.id)
    if not content.strip() and not image_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content or image is required")

    return serialize_message(message_repository.create(db, conversation_id, sender.id, content.strip(), image_url), sender)


def search_messages(db: Session, user_id: str, query: str) -> list[dict]:
    return serialize_messages(message_repository.search_for_user(db, user_id, query))


def update_message(db: Session, message_id: int, user_id: str, content: str) -> dict:
    message = message_repository.get_by_id(db, message_id)
    if not message or message.sender_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if message.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit deleted message")

    message.content = content.strip()
    return serialize_message(message_repository.save(db, message))


def delete_message(db: Session, message_id: int, user_id: str) -> dict:
    message = message_repository.get_by_id(db, message_id)
    if not message or message.sender_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    message.is_deleted = True
    message.content = ""
    message.image_url = None
    return serialize_message(message_repository.save(db, message))
