# tests/test_drill_generator.py
import pytest
from unittest.mock import MagicMock
from modules.drill_generator import DrillGenerator


@pytest.fixture
def generator():
    manifest = MagicMock()
    manifest.drill_mappings = {
        "verb_byc": "drills/pl_drill_byc.yaml",
        "verbal_aspect": "drills/pl_drill_aspekt.yaml",
        "chunk_accusative": "drills/pl_drill_biernik.yaml",
        "negation_genitive": "drills/pl_drill_dopelniacz.yaml",
        "locative_case": "drills/pl_drill_przypadki.yaml",
    }
    return DrillGenerator(manifest)


def test_drill_byc_a0(generator):
    drill = generator.generate("verb_byc", "A0", n=3)
    assert drill is not None
    assert len(drill.sentences) == 3
    assert all("jestem" in s or "jesteś" in s or "jest" in s or "jesteśmy" in s
               for s in drill.sentences)


def test_drill_aspekt_a2(generator):
    drill = generator.generate("verbal_aspect", "A2", n=3)
    assert drill is not None
    assert len(drill.sentences) == 3
    assert all("ale już" in s for s in drill.sentences)


def test_drill_biernik_a0(generator):
    drill = generator.generate("chunk_accusative", "A0", n=3)
    assert drill is not None
    assert len(drill.sentences) <= 3


def test_drill_no_mapping_returns_none(generator):
    drill = generator.generate("unknown_structure", "A0")
    assert drill is None


def test_drill_wrong_level_returns_none(generator):
    # A0 no tiene datos para locative_case
    drill = generator.generate("locative_case", "A0", n=3)
    assert drill is None or drill.sentences == []