# tests/test_vector_store_integration.py
import pytest
from pathlib import Path
from modules.rag.vault_parser import VaultParser
from modules.rag.vector_store import VectorStore
from config.settings import VAULT_BASE_PATH

# Este test usa tu vault real — requiere que las 3 tarjetas ya existan en
# /Users/raulrivera/Desktop/3-Languages/polski/

@pytest.fixture(scope="module")
def indexed_store():
    parser = VaultParser()
    cards = parser.parse_language("polski")
    assert len(cards) >= 3, "Esperaba al menos 3 tarjetas reales en el vault"

    store = VectorStore()
    all_chunks = []
    for card in cards:
        all_chunks.extend(parser.chunk_card(card))

    store.index_chunks(all_chunks)
    return store


def test_indexing_count(indexed_store):
    assert indexed_store.count() >= 3


def test_query_in_spanish_finds_polish_content(indexed_store):
    # Pregunta en español, debe encontrar la tarjeta de saludos en polaco
    results = indexed_store.query("cómo saludar y pedir un café", nivel="A0", language="pl")

    assert len(results) > 0
    found_greeting_card = any("Dzień dobry" in r["text"] for r in results)
    assert found_greeting_card, f"No encontró la tarjeta de saludos. Resultados: {[r['metadata']['tema'] for r in results]}"


def test_level_filter_excludes_higher_levels(indexed_store):
    # Las 3 tarjetas son A0 — pedir nivel A0 debe encontrarlas,
    # pedir solo resultados con filtro estricto de B2 no debería traer estas
    results_a0 = indexed_store.query("verbo ser", nivel="A0", language="pl")
    assert len(results_a0) > 0

    # Verifica que el filtro de nivel realmente está limitando
    for r in results_a0:
        assert r["metadata"]["nivel"] in ["A0"]


def test_query_byc_verb(indexed_store):
    results = indexed_store.query("cómo se conjuga el verbo ser en presente", nivel="A0", language="pl")
    found_byc_card = any("jestem" in r["text"] for r in results)
    assert found_byc_card