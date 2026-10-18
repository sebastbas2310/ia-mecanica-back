from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from services.chat_service import ChatConversationNotFound, ChatService


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, store, table):
        self.store = store
        self.table_name = table
        self.operation = "select"
        self.filters = []
        self.payload = None
        self.ordering = None
        self.row_range = None
        self.row_limit = None

    def select(self, columns):
        self.operation = "select"
        self.columns = columns
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, column, desc=False):
        self.ordering = (column, desc)
        return self

    def range(self, start, end):
        self.row_range = (start, end + 1)
        return self

    def limit(self, count):
        self.row_limit = count
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def execute(self):
        rows = self.store.tables[self.table_name]
        if self.operation == "insert":
            inserted = self.payload if isinstance(self.payload, list) else [self.payload]
            now = datetime.now(timezone.utc).isoformat()
            for item in inserted:
                row = dict(item)
                row.setdefault("sequence", len(rows) + 1)
                row.setdefault("created_at", now)
                if self.table_name == "chat_conversations":
                    row.setdefault("updated_at", now)
                rows.append(row)
            return FakeResponse(inserted)

        selected = [
            row
            for row in rows
            if all(row.get(key) == value for key, value in self.filters)
        ]
        if self.ordering:
            column, desc = self.ordering
            selected.sort(key=lambda row: row[column], reverse=desc)
        if self.row_range:
            start, end = self.row_range
            selected = selected[start:end]
        elif self.row_limit is not None:
            selected = selected[: self.row_limit]
        return FakeResponse(selected)


class FakeSupabase:
    def __init__(self):
        self.tables = {"chat_conversations": [], "chat_messages": []}
        self.access_tokens = []

    def table(self, table_name):
        return FakeQuery(self, table_name)


def test_conversation_is_saved_reloaded_and_scoped_to_user(monkeypatch):
    database = FakeSupabase()
    monkeypatch.setattr(
        "services.chat_service.get_user_client",
        lambda token: database.access_tokens.append(token) or database,
    )
    service = ChatService()
    service.graph.invoke = Mock(
        side_effect=[
            {"messages": [AIMessage(content="Primera respuesta.")]},
            {"messages": [AIMessage(content="Respuesta de seguimiento.")]},
        ]
    )

    _, conversation_id = service.answer(
        "Primera pregunta",
        user_id="user-1",
        access_token="user-jwt",
    )
    answer, returned_id = service.answer(
        "Pregunta de seguimiento",
        user_id="user-1",
        access_token="user-jwt",
        conversation_id=conversation_id,
    )

    assert returned_id == conversation_id
    assert answer == "Respuesta de seguimiento."
    assert database.access_tokens == ["user-jwt", "user-jwt"]
    assert database.tables["chat_conversations"][0]["title"] == "Primera pregunta"
    assert [item["role"] for item in database.tables["chat_messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert service.graph.invoke.call_args_list[1].args[0]["messages"] == [
        ("user", "Primera pregunta"),
        ("assistant", "Primera respuesta."),
        ("user", "Pregunta de seguimiento"),
    ]

    conversations = service.list_conversations(
        user_id="user-1", access_token="user-jwt", limit=50, offset=0
    )
    history = service.get_conversation(
        user_id="user-1",
        access_token="user-jwt",
        conversation_id=conversation_id,
        limit=100,
        offset=0,
    )
    assert conversations[0]["id"] == str(conversation_id)
    assert [item["content"] for item in history["messages"]] == [
        "Primera pregunta",
        "Primera respuesta.",
        "Pregunta de seguimiento",
        "Respuesta de seguimiento.",
    ]

    with pytest.raises(ChatConversationNotFound):
        service.get_conversation(
            user_id="another-user",
            access_token="other-jwt",
            conversation_id=conversation_id,
            limit=100,
            offset=0,
        )


def test_unknown_conversation_cannot_be_continued(monkeypatch):
    database = FakeSupabase()
    monkeypatch.setattr(
        "services.chat_service.get_user_client",
        Mock(return_value=database),
    )
    service = ChatService()
    service.graph.invoke = Mock()
    conversation_id = uuid4()

    with pytest.raises(ChatConversationNotFound):
        service.answer(
            "Intento de acceso a otra conversación",
            user_id="user-2",
            access_token="user-2-jwt",
            conversation_id=conversation_id,
        )

    service.graph.invoke.assert_not_called()
