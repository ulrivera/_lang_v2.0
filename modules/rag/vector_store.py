# modules/rag/vector_store.py
import logging
import chromadb
from chromadb.config import Settings
from config.settings import CHROMA_DIR
from modules.rag.embeddings import EmbeddingModel
from modules.rag.vault_parser import Chunk

logger = logging.getLogger(__name__)

COLLECTION_NAME = "lang_vault"


class VectorStore:
    """Interfaz sobre ChromaDB — indexación y recuperación de tarjetas del vault."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.embedder = EmbeddingModel()
        self.collection = self.client.get_or_create_collection(COLLECTION_NAME)

    def index_chunks(self, chunks: list[Chunk]) -> int:
        """Indexa una lista de chunks. Si un chunk_id ya existe, lo actualiza (upsert)."""
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = self.embedder.encode_batch(texts)
        ids = [c.chunk_id for c in chunks]
        metadatas = [c.metadata for c in chunks]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB")
        return len(chunks)

    def query(self, query_text: str, nivel: str = None, language: str = None,
              tipo: str = None, n_results: int = 5) -> list[dict]:
        """Recupera tarjetas relevantes, opcionalmente filtradas por metadata.

        Filtro de nivel: PRD v2.0 sección 4.2 — nivel <= nivel_usuario.
        Como Chroma no soporta comparación directa en metadata de string,
        se filtra por lista explícita de niveles permitidos."""

        query_embedding = self.embedder.encode(query_text)

        where_clause = self._build_where_clause(nivel, language, tipo)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause if where_clause else None
        )

        return self._format_results(results)

    def _build_where_clause(self, nivel: str, language: str, tipo: str) -> dict:
        conditions = []

        if nivel:
            allowed_levels = self._levels_up_to(nivel)
            conditions.append({"nivel": {"$in": allowed_levels}})

        if language:
            conditions.append({"language": language})

        if tipo:
            conditions.append({"tipo": tipo})

        if not conditions:
            return {}
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _levels_up_to(self, nivel: str) -> list[str]:
        """PRD v2.0 4.2 — un usuario en nivel X recupera tarjetas de X y todos los inferiores."""
        order = ["A0", "A2", "B2", "C2"]
        if nivel not in order:
            logger.warning(f"Unknown nivel '{nivel}' — defaulting to all levels")
            return order
        idx = order.index(nivel)
        return order[:idx + 1]

    def _format_results(self, raw_results: dict) -> list[dict]:
        formatted = []
        if not raw_results["documents"] or not raw_results["documents"][0]:
            return formatted

        for doc, metadata, distance in zip(
            raw_results["documents"][0],
            raw_results["metadatas"][0],
            raw_results["distances"][0]
        ):
            formatted.append({
                "text": doc,
                "metadata": metadata,
                "distance": distance
            })
        return formatted

    def count(self) -> int:
        return self.collection.count()