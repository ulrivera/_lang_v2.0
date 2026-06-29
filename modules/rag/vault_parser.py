# modules/rag/vault_parser.py
import logging
import hashlib
import frontmatter
from pathlib import Path
from dataclasses import dataclass
from config.settings import VAULT_BASE_PATH, VAULT_LANGUAGE_FOLDERS, CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_RATIO

logger = logging.getLogger(__name__)

REQUIRED_FRONTMATTER_FIELDS = ["nivel", "tipo", "tema"]

VALID_TIPOS = {
    "fonetica", "chunk", "conjugacion", "vocabulario",
    "colocacion", "drill", "pragmatica"
}

VALID_NIVELES = {"A0", "A2", "B2", "C2"}


@dataclass
class ParsedCard:
    """Una tarjeta del vault, ya validada, lista para chunking e indexación."""
    language_code: str
    nivel: str
    tipo: str
    tema: str
    palabras_clave: list
    fuente: str
    source_path: str
    content: str           # el cuerpo markdown, sin frontmatter
    content_hash: str      # para detectar cambios en re-indexación


@dataclass
class Chunk:
    """Fragmento de una tarjeta, listo para embedding."""
    chunk_id: str
    parent_card_path: str
    text: str
    chunk_index: int
    metadata: dict


class VaultParser:
    """Lee el vault de Obsidian, valida frontmatter, produce tarjetas parseadas."""

    def __init__(self, vault_base: Path = VAULT_BASE_PATH):
        self.vault_base = vault_base

    def parse_language(self, language_folder: str) -> list[ParsedCard]:
        """Parsea todas las tarjetas .md de la carpeta de un idioma."""
        if language_folder not in VAULT_LANGUAGE_FOLDERS:
            raise ValueError(f"Carpeta de idioma no mapeada en settings: {language_folder}")

        language_code = VAULT_LANGUAGE_FOLDERS[language_folder]
        folder_path = self.vault_base / language_folder

        if not folder_path.exists():
            raise FileNotFoundError(f"Vault folder not found: {folder_path}")

        cards = []
        md_files = sorted(folder_path.glob("*.md"))

        if not md_files:
            logger.warning(f"No .md files found in {folder_path}")

        for md_file in md_files:
            try:
                card = self._parse_file(md_file, language_code)
                cards.append(card)
            except ValueError as e:
                logger.error(f"Skipping {md_file.name}: {e}")
                continue

        logger.info(f"Parsed {len(cards)} cards from {folder_path}")
        return cards

    def _parse_file(self, path: Path, language_code: str) -> ParsedCard:
        with open(path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        self._validate_frontmatter(post.metadata, path)

        content_hash = hashlib.sha256(post.content.encode("utf-8")).hexdigest()[:12]

        return ParsedCard(
            language_code=language_code,
            nivel=post.metadata["nivel"],
            tipo=post.metadata["tipo"],
            tema=post.metadata["tema"],
            palabras_clave=post.metadata.get("palabras_clave", []),
            fuente=post.metadata.get("fuente", ""),
            source_path=str(path),
            content=post.content.strip(),
            content_hash=content_hash
        )

    def _validate_frontmatter(self, metadata: dict, path: Path) -> None:
        missing = [f for f in REQUIRED_FRONTMATTER_FIELDS if f not in metadata]
        if missing:
            raise ValueError(f"Missing required frontmatter fields: {missing}")

        if metadata["nivel"] not in VALID_NIVELES:
            raise ValueError(
                f"Invalid 'nivel': {metadata['nivel']} — must be one of {VALID_NIVELES}"
            )

        if metadata["tipo"] not in VALID_TIPOS:
            raise ValueError(
                f"Invalid 'tipo': {metadata['tipo']} — must be one of {VALID_TIPOS}"
            )

    def chunk_card(self, card: ParsedCard) -> list[Chunk]:
        """Divide una tarjeta en chunks de ~512 tokens con overlap.
        Para tarjetas cortas (caso común en A0-A2), retorna un solo chunk."""

        words = card.content.split()
        approx_tokens_per_word = 1.3  # aproximación para texto mixto polaco/markdown
        max_words = int(CHUNK_SIZE_TOKENS / approx_tokens_per_word)
        overlap_words = int(max_words * CHUNK_OVERLAP_RATIO)

        if len(words) <= max_words:
            # Caso común: la tarjeta entera es un solo chunk
            return [self._build_chunk(card, card.content, 0)]

        chunks = []
        start = 0
        index = 0
        while start < len(words):
            end = min(start + max_words, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(self._build_chunk(card, chunk_text, index))
            index += 1
            start = end - overlap_words if end < len(words) else end

        return chunks

    def _build_chunk(self, card: ParsedCard, text: str, index: int) -> Chunk:
        chunk_id = f"{card.language_code}_{card.content_hash}_{index}"
        metadata = {
            "nivel": card.nivel,
            "tipo": card.tipo,
            "tema": card.tema,
            "language": card.language_code,
            "source_path": card.source_path,
            "palabras_clave": ", ".join(card.palabras_clave) if card.palabras_clave else ""
        }
        return Chunk(
            chunk_id=chunk_id,
            parent_card_path=card.source_path,
            text=text,
            chunk_index=index,
            metadata=metadata
        )