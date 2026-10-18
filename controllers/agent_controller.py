from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError
from ollama import RequestError, ResponseError

from app.security import CurrentUser, get_current_user
from schemas import (
    ChatConversationOut,
    ChatConversationSummary,
    ChatRequest,
    ChatResponse,
)
from services.chat_service import (
    ChatConversationNotFound,
    ChatService,
    ChatStorageError,
)

router = APIRouter()
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El mensaje no puede estar vacío.",
        )

    try:
        answer, conversation_id = chat_service.answer(
            request.message,
            user_id=current_user.id,
            access_token=current_user.access_token,
            conversation_id=request.conversation_id,
        )
    except ChatConversationNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la conversación.",
        ) from error
    except ChatStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se pudo acceder al historial. Verifica la configuración "
                "de la base de datos de Supabase."
            ),
        ) from error
    except (HTTPError, RequestError, ResponseError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama no está disponible o no tiene cargado el modelo configurado.",
        ) from error

    return ChatResponse(answer=answer, conversation_id=conversation_id)


@router.get("/conversations", response_model=list[ChatConversationSummary])
def list_conversations(
    current_user: CurrentUser = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ChatConversationSummary]:
    try:
        conversations = chat_service.list_conversations(
            user_id=current_user.id,
            access_token=current_user.access_token,
            limit=limit,
            offset=offset,
        )
    except ChatStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se pudo acceder al historial. Verifica la configuración "
                "de la base de datos de Supabase."
            ),
        ) from error
    return [ChatConversationSummary(**item) for item in conversations]


@router.get(
    "/conversations/{conversation_id}", response_model=ChatConversationOut
)
def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ChatConversationOut:
    try:
        conversation = chat_service.get_conversation(
            user_id=current_user.id,
            access_token=current_user.access_token,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )
    except ChatConversationNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la conversación.",
        ) from error
    except ChatStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se pudo acceder al historial. Verifica la configuración "
                "de la base de datos de Supabase."
            ),
        ) from error
    return ChatConversationOut(**conversation)