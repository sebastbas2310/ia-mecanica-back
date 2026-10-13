from typing import Any, Dict, List, Optional
from supabase_client import supabase


class DocumentService:
    def __init__(self):
        self.table = supabase.table("documents")

    def create_document(self, user_id: str, title: str, content: Optional[str] = None):
        payload = {
            "user_id": user_id,
            "title": title,
            "content": content
        }
        result = self.table.insert(payload).execute()
        if not result.data:
            raise ValueError("No se pudo crear el documento")
        return result.data[0]

    def list_documents(self, user_id: str):
        result = self.table.select("*").eq("user_id", user_id).execute()
        return result.data

    def get_document(self, document_id: str, user_id: str):
        result = (
            self.table
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise ValueError("Documento no encontrado")
        return result.data[0]

    def update_document(self, document_id: str, user_id: str, title: Optional[str] = None, content: Optional[str] = None):
        payload = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content

        result = (
            self.table
            .update(payload)
            .eq("id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise ValueError("No se pudo actualizar el documento")
        return result.data[0]

    def delete_document(self, document_id: str, user_id: str):
        self.table.delete().eq("id", document_id).eq("user_id", user_id).execute()
        return {"message": "Documento eliminado", "document_id": document_id}