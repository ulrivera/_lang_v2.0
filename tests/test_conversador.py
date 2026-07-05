# tests/test_conversador.py
from core.conversador import Conversador, ConversadorResponse
from core.analizador import Diagnosis


def test_format_diagnosis_with_error():
    conv = Conversador.__new__(Conversador)
    diagnosis = Diagnosis(
        error_detected=True,
        error_type="red",
        error_form="byłem w sklep",
        correct_form="byłem w sklepie",
        structure="caso_locativo",
        tema_relacionado="caso_locativo"
    )
    result = conv._format_diagnosis(diagnosis)
    assert "byłem w sklepie" in result
    assert "RED" in result


def test_format_diagnosis_no_error():
    conv = Conversador.__new__(Conversador)
    diagnosis = Diagnosis(error_detected=False)
    result = conv._format_diagnosis(diagnosis)
    assert "Sin errores" in result


def test_format_rag_empty():
    conv = Conversador.__new__(Conversador)
    result = conv._format_rag_context([])
    assert "No se recuperaron" in result


def test_format_rag_with_results():
    conv = Conversador.__new__(Conversador)
    results = [{
        "text": "Dzień dobry significa buenos días.",
        "metadata": {"tipo": "chunk", "tema": "saludos", "nivel": "A0"},
        "distance": 0.12
    }]
    result = conv._format_rag_context(results)
    assert "Dzień dobry" in result
    assert "CHUNK" in result


def test_rag_deduplication():
    """Verifica que el segundo query RAG no duplica chunks ya recuperados."""
    conv = Conversador.__new__(Conversador)

    class MockVectorStore:
        def query(self, query_text, nivel, language, n_results):
            return [{"text": "mismo chunk", "metadata": {}, "distance": 0.1}]

    conv.vector_store = MockVectorStore()

    diagnosis = Diagnosis(
        error_detected=True,
        tema_relacionado="caso_locativo"
    )
    results = conv._query_rag("texto usuario", diagnosis, "A0", "pl")
    texts = [r["text"] for r in results]
    assert texts.count("mismo chunk") == 1  # sin duplicados