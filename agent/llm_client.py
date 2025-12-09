import os
from openai import OpenAI

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use environment variables directly
    pass


def get_openai_client():
    """Get OpenAI client from environment variables."""
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    api_version = os.getenv("OPENAI_API_VERSION")

    if not base_url or not api_key:
        raise ValueError(
            "Missing OpenAI configuration. Please set:\n"
            "  - OPENAI_BASE_URL\n"
            "  - OPENAI_API_KEY\n"
            "  - OPENAI_API_VERSION (optional)\n"
            "in your environment variables or .env file"
        )

    default_query = {}
    if api_version:
        default_query["api-version"] = api_version

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        default_query=default_query if default_query else None
    )


def call_chat_completions(text):
    """Call OpenAI chat completions API."""
    client = get_openai_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}],
        temperature=0,
    )
    return resp
