# tests/test_analizador.py
import pytest
from core.analizador import Analizador, Diagnosis


def test_parse_valid_json():
    analizador = Analizador.__new__(Analizador)  # sin conectar Ollama
    raw = '{"error_detected": true, "error_type": "red", "error_form": "byłem w sklep", "correct_form": "byłem w sklepie", "structure": "locative_case", "tema_relacionado": "caso_locativo"}'
    diagnosis = analizador._parse_response(raw)

    assert diagnosis.error_detected is True
    assert diagnosis.error_type == "red"
    assert diagnosis.tema_relacionado == "caso_locativo"
    assert diagnosis.parsed_successfully is True


def test_parse_json_with_extra_text():
    # El modelo a veces agrega texto antes/después aunque se le pida no hacerlo
    analizador = Analizador.__new__(Analizador)
    raw = 'Aquí está el diagnóstico:\n{"error_detected": false, "error_type": null, "error_form": null, "correct_form": null, "structure": null, "tema_relacionado": null}\nFin.'
    diagnosis = analizador._parse_response(raw)

    assert diagnosis.error_detected is False
    assert diagnosis.parsed_successfully is True


def test_parse_no_error_case():
    analizador = Analizador.__new__(Analizador)
    raw = '{"error_detected": false, "error_type": null, "error_form": null, "correct_form": null, "structure": null, "tema_relacionado": null}'
    diagnosis = analizador._parse_response(raw)

    assert diagnosis.error_detected is False
    assert diagnosis.error_type is None


def test_parse_malformed_json_does_not_crash():
    analizador = Analizador.__new__(Analizador)
    raw = "No puedo procesar esto correctamente, lo siento."
    diagnosis = analizador._parse_response(raw)

    assert diagnosis.parsed_successfully is False
    assert diagnosis.error_detected is False  # default seguro, no asume error