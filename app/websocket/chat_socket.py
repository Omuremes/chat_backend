from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from app.api.deps import authenticate_token_for_websocket
from app.db.session import SessionLocal
from app.repositories.conversation_repository import get_participant_ids
from app.schemas import MessageRead, WebSocketMessagePayload
from app.services.conversation_service import require_participant
from app.services.message_service import create_message
from app.websocket.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: int, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()
    user_id: str | None = None
    try:
        user = authenticate_token_for_websocket(token)
        user_id = user.id
        require_participant(db, conversation_id, user.id)
    except Exception:
        db.close()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_to_conversation(conversation_id, user_id, websocket)
    await manager.broadcast_to_others(
        conversation_id,
        user_id,
        {"type": "presence", "user_id": user_id, "is_online": True},
    )

    try:
        while True:
            raw_payload = await websocket.receive_json()
            try:
                payload = WebSocketMessagePayload.model_validate(raw_payload)
            except ValidationError:
                await websocket.send_json({"type": "error", "message": "Invalid websocket payload"})
                continue

            if payload.type == "typing":
                await manager.broadcast_to_others(
                    conversation_id,
                    user_id,
                    {"type": "typing", "user_id": user_id, "is_typing": bool(payload.is_typing)},
                )
                continue

            if payload.type != "message":
                await websocket.send_json({"type": "error", "message": "Unsupported websocket payload type"})
                continue

            message = create_message(
                db,
                conversation_id=conversation_id,
                sender=user,
                content=payload.content or "",
                image_url=payload.image_url,
            )
            encoded_message = jsonable_encoder(MessageRead.model_validate(message))
            await manager.broadcast_to_conversation(
                conversation_id,
                {"type": "message", "message": encoded_message, "client_id": payload.client_id},
            )
            for participant_id in get_participant_ids(db, conversation_id):
                await manager.broadcast_to_user(
                    participant_id,
                    {
                        "type": "conversation_updated",
                        "conversation_id": conversation_id,
                        "message": encoded_message,
                    },
                )
    except WebSocketDisconnect:
        pass
    finally:
        if user_id is not None:
            user_offline = manager.disconnect_from_conversation(conversation_id, user_id, websocket)
            if user_offline:
                await manager.broadcast_to_conversation(
                    conversation_id,
                    {"type": "presence", "user_id": user_id, "is_online": False},
                )
        db.close()


@router.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()
    try:
        user = authenticate_token_for_websocket(token)
    except Exception:
        db.close()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_user(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_user(user.id, websocket)
        db.close()
