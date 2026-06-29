# tests/test_loader.py
import pytest
from languages.loader import ManifestLoader


@pytest.fixture
def loader():
    return ManifestLoader()


def test_load_global_recast(loader):
    global_recast = loader.load_global_recast()
    assert "ROJO" in global_recast.red_label
    assert "AMBAR" in global_recast.amber_label or "ÁMBAR" in global_recast.amber_label
    assert "VERDE" in global_recast.green_label
    assert len(global_recast.red_definition) > 0


def test_load_polish_manifest(loader):
    manifest = loader.load("pl")
    assert manifest.language_code == "pl"
    assert manifest.tonal is False
    assert manifest.tts.primary_voice == "pl-PL-MarekNeural"


def test_pareto_by_level_includes_a0(loader):
    manifest = loader.load("pl")
    assert "A0" in manifest.pareto_by_level
    assert manifest.pareto_by_level["A0"].word_families == 150
    assert "B2" in manifest.pareto_by_level
    assert manifest.pareto_by_level["B2"].collocations_priority == "high"


def test_recast_rules_by_level(loader):
    manifest = loader.load("pl")

    a0_rules = manifest.get_recast_rules("A0")
    assert len(a0_rules.red) == 3
    assert "był" in a0_rules.red[0]

    a2_rules = manifest.get_recast_rules("A2")
    assert len(a2_rules.red) == 5
    assert any("Aspecto" in r for r in a2_rules.red)

    c2_rules = manifest.get_recast_rules("C2")
    assert any("Pan/Pani" in r for r in c2_rules.red)


def test_recast_rules_missing_level_returns_empty(loader):
    manifest = loader.load("pl")
    # B1 no está definido en el documento original — debe ser un set vacío, no error
    b1_rules = manifest.get_recast_rules("B1")
    assert b1_rules.red == []
    assert b1_rules.amber == []
    assert b1_rules.green == []


def test_missing_manifest_raises(loader):
    with pytest.raises(FileNotFoundError):
        loader.load("xx")