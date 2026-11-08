"""Gemini text embeddings, cached in SQLite and compared with cosine similarity."""

import hashlib
import math
from array import array

from google.genai import types

from app.core.logging import get_logger
from app.core.settings import MODEL_CONFIG
from app.infra.config import load_config
from app.infra.db import connect
from app.services import usage

logger = get_logger(__name__)

BATCH_SIZE = 50
MAX_CHARS = 6000


def embedding_config() -> tuple[str, int]:
    cfg = load_config(MODEL_CONFIG).get("embedding") or {}
    return cfg.get("model", "gemini-embedding-2"), int(cfg.get("dimensions", 768))


def to_blob(vector: list[float]) -> bytes:
    return array("f", vector).tobytes()


def from_blob(blob: bytes) -> list[float]:
    values = array("f")
    values.frombytes(blob)
    return values.tolist()


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _key(model: str, text: str) -> str:
    return hashlib.sha256(f"{model}\n{text}".encode()).hexdigest()


def _call_api(texts: list[str], model: str, dims: int) -> list[list[float]]:
    from app.services.generation.llm import _client

    usage.check_budget()
    result = _client().models.embed_content(
        model=model,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=dims),
    )
    usage.record_embedding(model, len(texts))
    return [list(e.values) for e in result.embeddings]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeddings for ``texts`` (same order), using and filling the cache."""
    model, dims = embedding_config()
    texts = [t[:MAX_CHARS] for t in texts]
    keys = [_key(model, t) for t in texts]
    found: dict[str, list[float]] = {}
    with connect() as conn:
        for i in range(0, len(keys), 500):
            chunk = keys[i : i + 500]
            rows = conn.execute(
                f"SELECT key, vector FROM embedding_cache WHERE key IN ({','.join('?' * len(chunk))})",
                chunk,
            ).fetchall()
            found.update({r["key"]: from_blob(r["vector"]) for r in rows})

    missing = [(k, t) for k, t in zip(keys, texts, strict=True) if k not in found]
    missing = list(dict(missing).items())  # dedupe identical texts
    for i in range(0, len(missing), BATCH_SIZE):
        batch = missing[i : i + BATCH_SIZE]
        vectors = _call_api([t for _, t in batch], model, dims)
        with connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO embedding_cache (key, model, vector) VALUES (?, ?, ?)",
                [
                    (k, model, to_blob(v))
                    for (k, _), v in zip(batch, vectors, strict=True)
                ],
            )
        found.update({k: v for (k, _), v in zip(batch, vectors, strict=True)})
    logger.info(
        "embeddings total=%s cached=%s new=%s",
        len(texts),
        len(texts) - len(missing),
        len(missing),
    )
    return [found[k] for k in keys]
