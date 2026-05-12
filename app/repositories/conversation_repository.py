from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.models import Conversation, ConversationParticipant, Message


def is_participant(db: Session, conversation_id: int, user_id: str) -> bool:
    return (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
        .first()
        is not None
    )


def find_private(db: Session, user_id: str, participant_id: str) -> Conversation | None:
    participant_counts = (
        db.query(
            ConversationParticipant.conversation_id.label("conversation_id"),
            func.count(ConversationParticipant.user_id).label("participant_count"),
        )
        .group_by(ConversationParticipant.conversation_id)
        .subquery()
    )

    matching_counts = (
        db.query(
            ConversationParticipant.conversation_id.label("conversation_id"),
            func.count(ConversationParticipant.user_id).label("matching_count"),
        )
        .filter(ConversationParticipant.user_id.in_([user_id, participant_id]))
        .group_by(ConversationParticipant.conversation_id)
        .subquery()
    )

    return (
        db.query(Conversation)
        .join(participant_counts, participant_counts.c.conversation_id == Conversation.id)
        .join(matching_counts, matching_counts.c.conversation_id == Conversation.id)
        .options(joinedload(Conversation.participants))
        .filter(participant_counts.c.participant_count == 2, matching_counts.c.matching_count == 2)
        .first()
    )


def create_private(db: Session, user_id: str, participant_id: str) -> Conversation:
    conversation = Conversation()
    db.add(conversation)
    db.flush()
    db.add_all(
        [
            ConversationParticipant(conversation_id=conversation.id, user_id=user_id),
            ConversationParticipant(conversation_id=conversation.id, user_id=participant_id),
        ]
    )
    db.commit()
    return conversation


def list_for_user(db: Session, user_id: str) -> list[Conversation]:
    return (
        db.query(Conversation)
        .join(ConversationParticipant)
        .options(joinedload(Conversation.participants))
        .filter(ConversationParticipant.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def get_with_participants(db: Session, conversation_id: int) -> Conversation | None:
    return (
        db.query(Conversation)
        .options(joinedload(Conversation.participants))
        .filter(Conversation.id == conversation_id)
        .first()
    )


def get_last_message(db: Session, conversation_id: int) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .first()
    )


def get_last_messages(db: Session, conversation_ids: list[int]) -> dict[int, Message]:
    if not conversation_ids:
        return {}

    ranked_messages = (
        db.query(
            Message.id.label("message_id"),
            func.row_number()
            .over(
                partition_by=Message.conversation_id,
                order_by=[Message.created_at.desc(), Message.id.desc()],
            )
            .label("rank"),
        )
        .filter(Message.conversation_id.in_(conversation_ids))
        .subquery()
    )

    messages = (
        db.query(Message)
        .join(ranked_messages, ranked_messages.c.message_id == Message.id)
        .filter(ranked_messages.c.rank == 1)
        .all()
    )
    return {message.conversation_id: message for message in messages}


def get_participant_ids(db: Session, conversation_id: int) -> list[str]:
    return [
        participant_id
        for (participant_id,) in db.query(ConversationParticipant.user_id)
        .filter(ConversationParticipant.conversation_id == conversation_id)
        .all()
    ]
