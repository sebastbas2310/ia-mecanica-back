
from typing import Any
from openai import OpenAI
import os

from supabase import Client


class ChatService:
    def __init__(self, supabase_client: Client):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.supabase = supabase_client

    def create_conversation(self, user_id: str, title: str = "Nueva conversación") -> dict[str, Any]:
        result = (
            self.supabase.table("chat_conversations")
            .insert({
                "user_id": user_id,
                "title": title,
            })
            .execute()
        )

        if not result.data:
            raise ValueError("No se pudo crear la conversación")

        return result.data[0]

    def get_conversations(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("chat_conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )

        return result.data

    def get_messages(
        self, conversation_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        conversation = (
            self.supabase.table("chat_conversations")
            .select("id")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not conversation.data:
            raise ValueError("Conversación no encontrada")

        result = (
            self.supabase.table("chat_messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )

        return result.data

    def send_message(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
    ) -> dict[str, Any]:
        # Verificar que la conversación pertenezca al usuario.
        conversation = (
            self.supabase.table("chat_conversations")
            .select("id")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not conversation.data:
            raise ValueError("Conversación no encontrada")

        # Guardar el mensaje del usuario.
        self.supabase.table("chat_messages").insert({
            "conversation_id": conversation_id,
            "role": "user",
            "content": message,
        }).execute()

        # Recuperar el historial para darle contexto a la IA.
        history = self.get_messages(conversation_id, user_id)

        messages = [
            {"role": item["role"], "content": item["content"]}
            for item in history
        ]

        # Consultar a OpenAI.
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        reply = response.choices[0].message.content

        if reply is None:
            raise RuntimeError("La IA no devolvió una respuesta")

        # Guardar la respuesta de la IA.
        self.supabase.table("chat_messages").insert({
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": reply,
        }).execute()

        # Actualizar la fecha de la conversación.
        self.supabase.table("chat_conversations").update({
            "updated_at": "now()",
        }).eq("id", conversation_id).eq("user_id", user_id).execute()

        return {
            "conversation_id": conversation_id,
            "reply": reply,
        }

def delete_conversation(self, conversation_id: str, user_id: str) -> dict:
    result = (
        self.supabase.table("chat_conversations")
        .delete()
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        raise ValueError("Conversación no encontrada")

    return {"deleted": True, "conversation_id": conversation_id}