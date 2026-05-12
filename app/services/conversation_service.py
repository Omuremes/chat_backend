from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Conversation
from app.repositories import conversation_repository, user_repository
from app.schemas import UserRead


def is_participant(db: Session, conversation_id: int, user_id: str) -> bool:
    return conversation_repository.is_participant(db, conversation_id, user_id)


def require_participant(db: Session, conversation_id: int, user_id: str) -> None:
    if not is_participant(db, conversation_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


def find_private_conversation(db: Session, user_id: str, participant_id: str) -> Conversation | None:
    return conversation_repository.find_private(db, user_id, participant_id)


def create_or_get_private_conversation(db: Session, current_user: UserRead, participant_id: str) -> Conversation:
    if participant_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create conversation with yourself")

    participant = user_repository.get_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = find_private_conversation(db, current_user.id, participant_id)
    if existing:
        return existing

    conversation = conversation_repository.create_private(db, current_user.id, participant_id)
    return get_conversation(db, conversation.id, current_user.id)


def list_conversations(db: Session, user_id: str) -> list[Conversation]:
    return conversation_repository.list_for_user(db, user_id)


def get_conversation(db: Session, conversation_id: int, user_id: str) -> Conversation:
    require_participant(db, conversation_id, user_id)
    conversation = conversation_repository.get_with_participants(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def serialize_conversation(db: Session, conversation: Conversation) -> dict:
    from app.services.message_service import serialize_message

    last_message = conversation_repository.get_last_message(db, conversation.id)
    participants = user_repository.get_by_ids({participant.user_id for participant in conversation.participants})
    return {
        "id": conversation.id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "participants": [user for user_id in [participant.user_id for participant in conversation.participants] if (user := participants.get(user_id))],
        "last_message": serialize_message(last_message) if last_message else None,
    }


def serialize_conversations(db: Session, conversations: list[Conversation]) -> list[dict]:
    from app.services.message_service import serialize_message

    conversation_ids = [conversation.id for conversation in conversations]
    last_messages = conversation_repository.get_last_messages(db, conversation_ids)
    user_ids = {
        participant.user_id
        for conversation in conversations
        for participant in conversation.participants
    }
    user_ids.update(message.sender_id for message in last_messages.values())
    users_by_id = user_repository.get_by_ids(user_ids)

    serialized = []
    for conversation in conversations:
        participants = [
            user
            for participant in conversation.participants
            if (user := users_by_id.get(participant.user_id))
        ]
        last_message = last_messages.get(conversation.id)
        serialized.append(
            {
                "id": conversation.id,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "participants": participants,
                "last_message": serialize_message(
                    last_message,
                    users_by_id.get(last_message.sender_id),
                    lookup_sender=False,
                )
                if last_message
                else None,
            }
        )
    return serialized
