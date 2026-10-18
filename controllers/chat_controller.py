
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import CurrentUser, get_current_user
from services.chat_service import ChatService
from supabase_client import get_user_client


router = APIRouter(prefix="/protected/chat", tags=["chat"])


class CreateConversationRequest(BaseModel):
    title: str = Field(default="Nueva conversación", min_length=1, max_length=150)


class SendMessageRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=10000)


def get_chat_service(
    user: CurrentUser = Depends(get_current_user),
) -> ChatService:
    supabase = get_user_client(user.access_token)
    return ChatService(supabase)


@router.post("/conversations", status_code=201)
def create_conversation(
    payload: CreateConversationRequest,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    try:
        return service.create_conversation(user.id, payload.title)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No se pudo crear la conversación",
        )


@router.get("/conversations")
def list_conversations(
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    try:
        return service.get_conversations(user.id)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No se pudieron consultar las conversaciones",
        )


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    try:
        return service.get_messages(conversation_id, user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No se pudieron consultar los mensajes",
        )


@router.post("/messages")
def send_message(
    payload: SendMessageRequest,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    try:
        return service.send_message(
            user_id=user.id,
            conversation_id=payload.conversation_id,
            message=payload.message,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No se pudo procesar el mensaje",
        )
