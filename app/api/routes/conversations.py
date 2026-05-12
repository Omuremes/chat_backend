from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas import ConversationCreate, ConversationRead, UserRead
from app.services.conversation_service import (
    create_or_get_private_conversation,
    get_conversation,
    list_conversations,
    serialize_conversation,
    serialize_conversations,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def read_conversations(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return serialize_conversations(db, list_conversations(db, current_user.id))


@router.post("", response_model=ConversationRead)
def create_conversation(
    payload: ConversationCreate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = create_or_get_private_conversation(db, current_user, payload.participant_id)
    return serialize_conversation(db, conversation)


@router.get("/{conversation_id}", response_model=ConversationRead)
def read_conversation(
    conversation_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = get_conversation(db, conversation_id, current_user.id)
    return serialize_conversation(db, conversation)
