"""Gemini 호출을 한곳에 모은다. 요약과 하루치 브리핑이 같이 쓴다."""

from __future__ import annotations

from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)

# 요약은 판단이 복잡한 일이 아니다. 생각을 짧게 시켜 토큰을 아낀다.
THINKING_LEVEL = "low"


def model_name() -> str:
    return settings.gemini_model


def make_client() -> genai.Client:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY 가 없다. .env 에 넣거나 환경변수로 내보낼 것.")
    return genai.Client(api_key=settings.gemini_api_key)


def generate(
    client: genai.Client,
    *,
    system: str,
    contents: list[types.Part] | str,
    schema: type[T],
    max_tokens: int = 2_000,
) -> tuple[T, types.GenerateContentResponseUsageMetadata | None]:
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
            # 도구를 안 쓰는데 SDK 가 매번 AFC 경고를 찍는다.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    parsed = response.parsed
    if not isinstance(parsed, schema):
        raise ValueError(f"구조화 응답을 못 받았다: {(response.text or '')[:200]!r}")
    return parsed, response.usage_metadata
