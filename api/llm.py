"""Single AsyncOpenAI client pointed at NVIDIA NIM, plus the embeddings helper.

Every other module imports `llm` from here so the client is shared.
"""

from openai import AsyncOpenAI

from config import EMBED_MODEL, NVIDIA_API_KEY, NVIDIA_BASE_URL

llm = AsyncOpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)


async def embed_texts(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    """Embed a batch of texts. `input_type` is either 'passage' (for indexing)
    or 'query' (for retrieval) — required by NVIDIA's embedqa models."""
    if not texts:
        return []
    resp = await llm.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
        encoding_format="float",
        extra_body={"input_type": input_type, "truncate": "END"},
    )
    return [d.embedding for d in resp.data]
