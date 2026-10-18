from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from httpx import HTTPError
from ollama import RequestError, ResponseError
from starlette.concurrency import run_in_threadpool

from app.security import CurrentUser, get_current_user
from schemas import (
    ChatConversationOut,
    ChatConversationSummary,
    ChatAttachmentRequest,
    ChatRequest,
    ChatResponse,
)
from services.chat_attachments import (
    MAX_ATTACHMENT_BYTES,
    ChatAttachmentError,
    extract_attachment_text,
    format_attachment_message,
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


@router.post("/chat/attachment", response_model=ChatResponse)
async def chat_with_attachment(
    message: str = Form(..., min_length=1, max_length=4000),
    conversation_id: UUID | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    if not message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El mensaje no puede estar vacío.",
        )
    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    try:
        extracted_text = extract_attachment_text(file.filename or "", content)
    except ChatAttachmentError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    request = ChatAttachmentRequest(
        message=format_attachment_message(
            message, file.filename or "adjunto", extracted_text
        ),
        conversation_id=conversation_id,
    )
    try:
        answer, returned_conversation_id = await run_in_threadpool(
            chat_service.answer,
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
    return ChatResponse(
        answer=answer, conversation_id=returned_conversation_id
    )


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


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_conversation(
    conversation_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    try:
        chat_service.delete_conversation(
            user_id=current_user.id,
            access_token=current_user.access_token,
            conversation_id=conversation_id,
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