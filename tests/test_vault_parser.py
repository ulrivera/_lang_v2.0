# tests/test_vault_parser.py
import pytest
import tempfile
from pathlib import Path
from modules.rag.vault_parser import VaultParser

SAMPLE_CARD = """---
nivel: A0
tipo: chunk
tema: saludos_cortesia_basica
palabras_clave:
  - "dzień dobry"
  - "przepraszam"
fuente: "Test"
fecha: 2026-06-28
---

# Saludos de prueba

Dzień dobry significa buenos días.
"""

SAMPLE_CARD_INVALID_TIPO = """---
nivel: A0
tipo: tipo_que_no_existe
tema: prueba
---

Contenido de prueba.
"""

SAMPLE_CARD_MISSING_FIELD = """---
nivel: A0
tema: prueba
---

Falta el campo tipo.
"""


@pytest.fixture
def temp_vault():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_base = Path(tmpdir)
        polski_dir = vault_base / "polski"
        polski_dir.mkdir()
        yield vault_base, polski_dir


def test_parse_valid_card(temp_vault):
    vault_base, polski_dir = temp_vault
    (polski_dir / "saludos.md").write_text(SAMPLE_CARD, encoding="utf-8")

    parser = VaultParser(vault_base=vault_base)
    cards = parser.parse_language("polski")

    assert len(cards) == 1
    assert cards[0].language_code == "pl"
    assert cards[0].nivel == "A0"
    assert cards[0].tipo == "chunk"
    assert "Dzień dobry" in cards[0].content


def test_invalid_tipo_skipped(temp_vault):
    vault_base, polski_dir = temp_vault
    (polski_dir / "bad.md").write_text(SAMPLE_CARD_INVALID_TIPO, encoding="utf-8")

    parser = VaultParser(vault_base=vault_base)
    cards = parser.parse_language("polski")

    assert len(cards) == 0  # se descarta, no debe crashear el proceso completo


def test_missing_field_skipped(temp_vault):
    vault_base, polski_dir = temp_vault
    (polski_dir / "incomplete.md").write_text(SAMPLE_CARD_MISSING_FIELD, encoding="utf-8")

    parser = VaultParser(vault_base=vault_base)
    cards = parser.parse_language("polski")

    assert len(cards) == 0


def test_unmapped_language_folder_raises(temp_vault):
    vault_base, _ = temp_vault
    parser = VaultParser(vault_base=vault_base)

    with pytest.raises(ValueError):
        parser.parse_language("idioma_no_mapeado")


def test_chunk_short_card_returns_single_chunk(temp_vault):
    vault_base, polski_dir = temp_vault
    (polski_dir / "saludos.md").write_text(SAMPLE_CARD, encoding="utf-8")

    parser = VaultParser(vault_base=vault_base)
    cards = parser.parse_language("polski")
    chunks = parser.chunk_card(cards[0])

    assert len(chunks) == 1
    assert chunks[0].metadata["tipo"] == "chunk"
    assert chunks[0].metadata["nivel"] == "A0"


def test_chunk_long_card_splits_with_overlap(temp_vault):
    vault_base, polski_dir = temp_vault
    long_content = " ".join(["słowo"] * 1000)  # ~1000 palabras, fuerza split
    long_card = f"""---
nivel: B2
tipo: vocabulario
tema: prueba_larga
---

{long_content}
"""
    (polski_dir / "largo.md").write_text(long_card, encoding="utf-8")

    parser = VaultParser(vault_base=vault_base)
    cards = parser.parse_language("polski")
    chunks = parser.chunk_card(cards[0])

    assert len(chunks) > 1
    # verifica que hay overlap real entre chunks consecutivos
    words_chunk0 = chunks[0].text.split()
    words_chunk1 = chunks[1].text.split()
    assert words_chunk0[-1] == words_chunk1[0] or len(set(words_chunk0[-20:]) & set(words_chunk1[:20])) > 0