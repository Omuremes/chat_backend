from fastapi import APIRouter

from app.api.routes import conversations, health, messages, storage, users
from app.websocket import chat_socket

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(storage.router)
api_router.include_router(chat_socket.router)
