import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import httpx
from postgrest import APIError

from agents.agent import build_graph
from supabase_client import get_user_client

logger = logging.getLogger(__name__)
MAX_CONTEXT_MESSAGES = 20


class ChatConversationNotFound(Exception):
    pass


class ChatStorageError(Exception):
    pass


class ChatService:
    def __init__(self) -> None:
        self.graph = build_graph()

    def answer(
        self,
        message: str,
        user_id: str,
        access_token: str,
        conversation_id: UUID | None = None,
    ) -> tuple[str, UUID]:
        create_conversation = conversation_id is None
        conversation_id = conversation_id or uuid4()
        client = self._get_client(access_token)

        conversation_exists = self._conversation_exists(
            client, user_id, conversation_id
        )
        if conversation_exists:
            history = self._load_context(client, user_id, conversation_id)
        elif not create_conversation:
            raise ChatConversationNotFound
        else:
            history = []

        messages = [(row["role"], row["content"]) for row in history]
        messages.append(("user", message))
        result = self.graph.invoke(
            {"messages": messages}
        )

        answer = result["messages"][-1].content
        if not isinstance(answer, str):
            raise TypeError("El modelo devolvió una respuesta que no es texto.")

        self._save_turn(
            client,
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            answer=answer,
            create_conversation=create_conversation,
        )
        return answer, conversation_id

    def list_conversations(
        self, user_id: str, access_token: str, limit: int, offset: int
    ) -> list[dict]:
        client = self._get_client(access_token)
        try:
            response = (
                client.table("chat_conversations")
                .select("id,title,created_at,updated_at")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as error:
            raise self._storage_error(error) from error
        return response.data

    def get_conversation(
        self,
        user_id: str,
        access_token: str,
        conversation_id: UUID,
        limit: int,
        offset: int,
    ) -> dict:
        client = self._get_client(access_token)
        try:
            conversation_response = (
                client.table("chat_conversations")
                .select("id,title,created_at,updated_at")
                .eq("id", str(conversation_id))
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if not conversation_response.data:
                raise ChatConversationNotFound

            messages_response = (
                client.table("chat_messages")
                .select("id,role,content,created_at")
                .eq("conversation_id", str(conversation_id))
                .eq("user_id", user_id)
                .order("sequence")
                .range(offset, offset + limit - 1)
                .execute()
            )
        except ChatConversationNotFound:
            raise
        except (APIError, httpx.HTTPError) as error:
            raise self._storage_error(error) from error

        return {
            **conversation_response.data[0],
            "messages": messages_response.data,
            "next_offset": (
                offset + limit if len(messages_response.data) == limit else None
            ),
        }

    def _conversation_exists(self, client, user_id: str, conversation_id: UUID) -> bool:
        try:
            response = (
                client.table("chat_conversations")
                .select("id")
                .eq("id", str(conversation_id))
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as error:
            raise self._storage_error(error) from error
        return bool(response.data)

    def _load_context(self, client, user_id: str, conversation_id: UUID) -> list[dict]:
        try:
            response = (
                client.table("chat_messages")
                .select("role,content")
                .eq("conversation_id", str(conversation_id))
                .eq("user_id", user_id)
                .order("sequence", desc=True)
                .limit(MAX_CONTEXT_MESSAGES)
                .execute()
            )
        except (APIError, httpx.HTTPError) as error:
            raise self._storage_error(error) from error
        return list(reversed(response.data))

    def _save_turn(
        self,
        client,
        user_id: str,
        conversation_id: UUID,
        message: str,
        answer: str,
        create_conversation: bool,
    ) -> None:
        created_at = datetime.now(timezone.utc)
        messages = [
            {
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "role": "user",
                "content": message,
                "created_at": created_at.isoformat(),
            },
            {
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "role": "assistant",
                "content": answer,
                "created_at": (created_at + timedelta(microseconds=1)).isoformat(),
            },
        ]
        try:
            if create_conversation:
                title = " ".join(message.split())[:120]
                client.table("chat_conversations").insert(
                    {
                        "id": str(conversation_id),
                        "user_id": user_id,
                        "title": title,
                    }
                ).execute()
            client.table("chat_messages").insert(messages).execute()
        except (APIError, httpx.HTTPError) as error:
            raise self._storage_error(error) from error

    def _get_client(self, access_token: str):
        try:
            return get_user_client(access_token)
        except (RuntimeError, APIError, httpx.HTTPError) as error:
            raise self._storage_error(error) from error

    @staticmethod
    def _storage_error(error: Exception) -> ChatStorageError:
        logger.error("No se pudo acceder al historial de chat (%s)", type(error).__name__)
        return ChatStorageError("No se pudo acceder al historial de conversaciones.")