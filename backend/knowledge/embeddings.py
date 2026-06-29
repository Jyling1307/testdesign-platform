"""ZhipuAI embedding wrapper using OpenAI-compatible SDK."""

from openai import OpenAI
from config import settings


def get_embedding_client():
    return OpenAI(
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
    )


def embed_texts(texts, model=None, batch_size=20):
    """Embed a list of texts.

    Args:
        texts: List of strings to embed
        model: Override model name
        batch_size: Number of texts per API call

    Returns:
        list: List of embedding vectors
    """
    client = get_embedding_client()
    model = model or settings.EMBEDDING_MODEL
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def embed_query(text, model=None):
    """Embed a single query text."""
    return embed_texts([text], model=model)[0]
