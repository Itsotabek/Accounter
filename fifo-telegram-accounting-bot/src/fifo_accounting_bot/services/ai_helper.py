from __future__ import annotations

from dataclasses import dataclass


LANGUAGE_NAMES = {
    "en": "English",
    "uz": "Uzbek",
    "tr": "Turkish",
    "it": "Italian",
    "ru": "Russian",
}


@dataclass(frozen=True, slots=True)
class AIConfig:
    api_key: str
    model: str
    max_output_tokens: int = 450


class AIHelper:
    """On-demand, explanation-only AI. It has no database or write tools."""

    def __init__(self, config: AIConfig):
        self._config = config
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self._config.api_key)

    def explain(self, question: str, language: str, context: str = "") -> str:
        if not self.available:
            raise RuntimeError("AI is not configured by the bot owner.")
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._config.api_key)

        language_name = LANGUAGE_NAMES.get(language, "English")
        instructions = (
            "You are the read-only help assistant inside Accounter, a double-entry "
            "bookkeeping bot with FIFO inventory. "
            "Answer only the user's explicit question in clear, friendly language. "
            "Explain FIFO inventory, stock, revenue, COGS, and gross profit simply. "
            "Never claim to edit records, never invent figures, and never provide legal or tax advice. "
            f"Reply in {language_name}. Keep the answer concise and use a small example when helpful."
        )
        user_input = question.strip()
        if context:
            user_input += "\n\nRead-only calculated context from the bot:\n" + context
        response = self._client.responses.create(
            model=self._config.model,
            instructions=instructions,
            input=user_input,
            store=False,
            max_output_tokens=self._config.max_output_tokens,
        )
        output = (response.output_text or "").strip()
        if not output:
            raise RuntimeError("The AI service returned an empty explanation.")
        return output
