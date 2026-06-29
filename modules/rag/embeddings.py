# modules/rag/embeddings.py
import logging
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper sobre el modelo de embeddings multilingüe.
    Carga una sola vez, se reutiliza para todas las consultas e indexación."""

    _instance = None

    def __new__(cls):
        # Singleton — el modelo pesa ~470MB, no queremos cargarlo más de una vez
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
        return cls._instance

    def _ensure_loaded(self) -> None:
        if self._model is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self._model = SentenceTransformer(EMBEDDING_MODEL)

    def encode(self, text: str) -> list:
        self._ensure_loaded()
        return self._model.encode(text).tolist()

    def encode_batch(self, texts: list[str]) -> list[list]:
        self._ensure_loaded()
        return self._model.encode(texts).tolist()