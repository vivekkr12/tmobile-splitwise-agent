import os
from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam

# Try to load .env file if it exists (override=True to override OS env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    # dotenv not installed, will use environment variables directly
    pass


def get_openai_client():
    """Get OpenAI client from environment variables."""
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")

    if not base_url or not api_key:
        raise ValueError(
            "Missing OpenAI configuration. Please set:\n"
            "  - OPENAI_BASE_URL\n"
            "  - OPENAI_API_KEY\n"
            "  - OPENAI_MODEL_NAME\n"
            "in your environment variables or .env file"
        )

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


def call_chat_completions(text: str):
    """Call OpenAI chat completions API."""
    client = get_openai_client()
    model_name = os.getenv("OPENAI_MODEL_NAME")

    user_message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": text,
    }

    resp = client.chat.completions.create(
        model=model_name,
        messages=[user_message],
        temperature=0,
    )
    return resp
