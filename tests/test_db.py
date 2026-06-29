# tests/test_db.py
import pytest
import tempfile
from pathlib import Path
from data.db import Database
from data.models import Session, LoraTrainingCandidate, VaultCard


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    database = Database(db_path)
    database.connect()
    yield database
    database.disconnect()
    db_path.unlink()


def test_profile_creation(db):
    profile = db.get_or_create_profile(user_l1="es", default_level="A0")
    assert profile["user_l1"] == "es"
    assert profile["current_level"] == "A0"


def test_profile_idempotent(db):
    db.get_or_create_profile(user_l1="es")
    db.get_or_create_profile(user_l1="fr")  # no debe crear un segundo perfil
    count = db._conn().execute("SELECT COUNT(*) as c FROM user_profile").fetchone()["c"]
    assert count == 1


def test_session_with_l1(db):
    session = Session(language="pl", level="A2", modality="chat_chat", user_l1="es")
    session_id = db.create_session(session)
    last = db.get_last_session("pl")
    assert last["user_l1"] == "es"


def test_lora_candidate_logging(db):
    candidate = LoraTrainingCandidate(
        module="analizador",
        full_prompt="...",
        raw_output='{"error_detected": true}',
        parsed_successfully=True,
        validation_source="auto"
    )
    db.log_lora_candidate(candidate)
    assert db.count_lora_candidates(only_successful=True) == 1


def test_vault_card_registration(db):
    card = VaultCard(
        language="pl", level="A2", card_type="vocabulario",
        tema="familia", source_path="/vault/pl/familia.md", chroma_id="abc123"
    )
    db.register_vault_card(card)
    cards = db.get_cards_by_language("pl")
    assert len(cards) == 1
    assert cards[0]["tema"] == "familia"