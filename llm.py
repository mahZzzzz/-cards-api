
import os
import logging

import instructor

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_models() -> list[str]:
    """Read ordered model names from environment variables."""

    models = os.getenv("GROQ_MODELS", "")

    if models.strip():
        return [
            name.strip()
            for name in models.split(",")
            if name.strip()
        ]

    return DEFAULT_MODELS.copy()


def chat_completion(
    messages: list[dict],
    **kwargs,
):
    """
    Call Groq with automatic model fallback.

    Send the complete conversation on every request.
    """

    client = Groq(
        api_key=os.environ["GROQ_API_KEY"],
        timeout=90.0,
        max_retries=0,
    )

    errors = []

    for model in get_models():
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )

            usage = response.usage

            logger.info(
                "Model: %s | Input tokens: %s | Output tokens: %s",
                model,
                usage.prompt_tokens if usage else "unknown",
                usage.completion_tokens if usage else "unknown",
            )

            return response

        except Exception as error:
            errors.append(f"{model}: {error}")

            logger.warning(
                "Model %s failed: %s",
                model,
                error,
            )

    raise RuntimeError(
        "All configured models failed:\n"
        + "\n".join(errors)
    )


def structured_completion(
    messages: list[dict],
    response_model: type[BaseModel],
    max_retries: int = 2,
    **kwargs,
) -> BaseModel:
    """
    Generate a Pydantic-validated response using Instructor.

    Instructor retries invalid structured outputs.
    If a model fails, try the next configured model.
    """

    openai_client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url=GROQ_BASE_URL,
        timeout=90.0,
        max_retries=0,
    )

    client = instructor.from_openai(
        openai_client,
        mode=instructor.Mode.JSON,
    )

    errors = []

    for model in get_models():
        try:
            result = client.chat.completions.create(
                model=model,
                messages=messages,
                response_model=response_model,
                max_retries=max_retries,
                **kwargs,
            )

            logger.info(
                "Structured output validated successfully | Model: %s",
                model,
            )

            return result

        except Exception as error:
            errors.append(f"{model}: {error}")

            logger.warning(
                "Structured completion failed for model %s: %s",
                model,
                error,
            )

    raise RuntimeError(
        "All models failed to generate a valid structured response:\n"
        + "\n".join(errors)
    )
