from typing import List, Dict, Any
import os
from openai import OpenAI

class ChatService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def send_message(self, message: str, conversation: List[Dict[str, str]] | None = None):
        messages = conversation or []

        messages.append({
            "role": "user",
            "content": message
        })

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        reply = response.choices[0].message.content

        messages.append({
            "role": "assistant",
            "content": reply
        })

        return {
            "reply": reply,
            "conversation": messages
        }