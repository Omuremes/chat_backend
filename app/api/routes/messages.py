from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.repositories.conversation_repository import get_participant_ids
from app.schemas import MessageCreate, MessageRead, MessageUpdate, UserRead
from app.services.message_service import create_message, delete_message, list_messages, search_messages, update_message
from app.websocket.manager import manager

router = APIRouter(tags=["messages"])


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def read_messages(
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return list_messages(db, conversation_id, current_user.id, limit=limit, offset=offset)


@router.get("/messages/search", response_model=list[MessageRead])
def search_my_messages(
    q: str = Query(min_length=1, max_length=120),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return search_messages(db, current_user.id, q)


async def broadcast_message_change(db: Session, message: dict, event_type: str, client_id: str | None = None) -> None:
    encoded_message = jsonable_encoder(MessageRead.model_validate(message))
    payload = {"type": "message", "message": encoded_message, "event": event_type, "client_id": client_id}
    await manager.broadcast_to_conversation(message["conversation_id"], payload)
    for participant_id in get_participant_ids(db, message["conversation_id"]):
        await manager.broadcast_to_user(
            participant_id,
            {
                "type": "conversation_updated",
                "conversation_id": message["conversation_id"],
                "message": encoded_message,
                "event": event_type,
                "client_id": client_id,
            },
        )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead)
async def send_message(
    conversation_id: int,
    payload: MessageCreate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    message = create_message(
        db,
        conversation_id=conversation_id,
        sender=current_user,
        content=payload.content,
        image_url=payload.image_url,
    )
    await broadcast_message_change(db, message, "created", payload.client_id)
    return message


@router.patch("/messages/{message_id}", response_model=MessageRead)
async def edit_message(
    message_id: int,
    payload: MessageUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    message = update_message(db, message_id, current_user.id, payload.content)
    await broadcast_message_change(db, message, "updated")
    return message


@router.delete("/messages/{message_id}", response_model=MessageRead)
async def remove_message(
    message_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    message = delete_message(db, message_id, current_user.id)
    await broadcast_message_change(db, message, "deleted")
    return message
