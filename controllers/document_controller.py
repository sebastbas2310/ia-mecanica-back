from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
service = DocumentService()


class CreateDocumentRequest(BaseModel):
    user_id: str
    title: str = Field(..., min_length=1, max_length=200)
    content: Optional[str] = None


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(data: CreateDocumentRequest):
    try:
        return service.create_document(
            user_id=data.user_id,
            title=data.title,
            content=data.content
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
def list_documents(user_id: str):
    try:
        return service.list_documents(user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{document_id}")
def get_document(document_id: str, user_id: str):
    try:
        return service.get_document(document_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{document_id}")
def update_document(document_id: str, user_id: str, data: UpdateDocumentRequest):
    try:
        return service.update_document(
            document_id=document_id,
            user_id=user_id,
            title=data.title,
            content=data.content
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{document_id}")
def delete_document(document_id: str, user_id: str):
    try:
        return service.delete_document(document_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))