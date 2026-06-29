# data/models.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class UserProfile:
    """Perfil del usuario — PRD v2.0 sección 3, campos obligatorios L1 y nivel."""
    user_l1: str                  # idioma base, ej. "es"
    current_level: str            # A0-C2
    id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Session:
    language: str
    level: str
    modality: str
    user_l1: str                  # nuevo en v2 — viene del perfil
    id: Optional[int] = None
    date: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: int = 0
    summary: Optional[str] = None
    hook_next_session: Optional[str] = None
    red_error_count: int = 0
    total_items: int = 0
    romanization_active: bool = False


@dataclass
class SessionItem:
    session_id: int
    item_type: str
    form: str
    correct: bool
    id: Optional[int] = None
    error_type: Optional[str] = None
    recast_applied: Optional[str] = None
    error_form: Optional[str] = None
    correct_form: Optional[str] = None
    structure: Optional[str] = None


@dataclass
class LoraTrainingCandidate:
    """Captura cada llamada al SLM para futuro entrenamiento de adaptador."""
    module: str                       # "analizador" o "conversador"
    full_prompt: str
    raw_output: str
    parsed_successfully: bool
    id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    validated_output: Optional[str] = None
    validation_source: Optional[str] = None   # "auto" o "manual"
    used_for_training: bool = False


@dataclass
class VaultCard:
    """Representa una tarjeta indexada del vault — metadata espejo de lo que vive en Chroma."""
    language: str
    level: str
    card_type: str                # conjugacion, vocabulario, drill_estructural
    tema: str
    source_path: str              # path al archivo .md original
    chroma_id: str
    id: Optional[int] = None
    indexed_at: str = field(default_factory=lambda: datetime.now().isoformat())