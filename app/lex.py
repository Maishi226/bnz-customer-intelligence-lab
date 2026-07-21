from __future__ import annotations

import json
import os
from typing import Any

import boto3
from botocore.config import Config


class LexService:
    def __init__(self) -> None:
        self.region = os.getenv("AWS_REGION", "ap-southeast-2")
        self.profile = os.getenv("AWS_PROFILE", "").strip()
        self.bot_id = os.getenv("LEX_BOT_ID", "").strip()
        self.alias_id = os.getenv("LEX_BOT_ALIAS_ID", "").strip()
        self.locale_id = os.getenv("LEX_LOCALE_ID", "en_AU")

    @property
    def configured(self) -> bool:
        return bool(self.bot_id and self.alias_id)

    def _client(self):
        session = boto3.Session(
            profile_name=self.profile or None,
            region_name=self.region,
        )
        return session.client(
            "lexv2-runtime",
            config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 2}),
        )

    def chat(self, message: str, session_id: str, context: dict[str, Any]) -> dict[str, str]:
        if not self.configured:
            return {
                "reply": "Lex is ready to connect after you add the bot ID and alias ID. For now, review the campaign risks and safer rewrite shown in the Lab.",
                "source": "local Lex placeholder",
            }
        compact_context = json.dumps(context, separators=(",", ":"))[:10000]
        response = self._client().recognize_text(
            botId=self.bot_id,
            botAliasId=self.alias_id,
            localeId=self.locale_id,
            sessionId=session_id,
            text=message,
            sessionState={"sessionAttributes": {"simulationContext": compact_context}},
        )
        messages = response.get("messages", [])
        reply = " ".join(item.get("content", "") for item in messages if item.get("content")).strip()
        return {
            "reply": reply or "I can explain this campaign and its customer-risk review.",
            "source": "Amazon Lex V2 + Lambda",
        }

