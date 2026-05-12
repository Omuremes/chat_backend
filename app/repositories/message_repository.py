from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import Conversation, ConversationParticipant, Message


def list_for_conversation(db: Session, conversation_id: int, limit: int, offset: int) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def create(db: Session, conversation_id: int, sender_id: str, content: str, image_url: str | None) -> Message:
    message = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        image_url=image_url,
    )
    db.add(message)
    conversation = db.get(Conversation, conversation_id)
    if conversation:
        conversation.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(message)
    return get_by_id(db, message.id) or message


def get_by_id(db: Session, message_id: int) -> Message | None:
    return db.query(Message).filter(Message.id == message_id).first()


def search_for_user(db: Session, user_id: str, query: str) -> list[Message]:
    return (
        db.query(Message)
        .join(ConversationParticipant, ConversationParticipant.conversation_id == Message.conversation_id)
        .filter(
            Message.is_deleted.is_(False),
            Message.content.ilike(f"%{query}%"),
            ConversationParticipant.user_id == user_id,
        )
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )


def save(db: Session, message: Message) -> Message:
    db.commit()
    db.refresh(message)
    return message
