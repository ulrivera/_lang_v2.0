# languages/base_manifest.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TTSConfig:
    engine: str
    primary_voice: str
    secondary_voice: Optional[str] = None


@dataclass
class MorphologyConfig:
    bottleneck: str
    red_zone_structures: list = field(default_factory=list)
    drill_patterns: list = field(default_factory=list)


@dataclass
class ParetoLevel:
    word_families: int
    source_corpus: str
    collocations_priority: Optional[str] = None
    focus: Optional[str] = None


@dataclass
class RecastRuleSet:
    """Las 3 zonas de un nivel específico."""
    red: list = field(default_factory=list)
    amber: list = field(default_factory=list)
    green: list = field(default_factory=list)


@dataclass
class LanguageManifest:
    language_code: str
    language_name: str
    family: str
    tonal: bool
    tts: TTSConfig
    morphology: MorphologyConfig

    # Pareto por nivel — ahora soporta A0-C2 según PRD v2.0
    pareto_by_level: dict = field(default_factory=dict)   # {"A0": ParetoLevel, "A2": ParetoLevel, ...}

    # Recast por nivel — estructura nueva de v2, antes era plana en v1
    recast_by_level: dict = field(default_factory=dict)   # {"A0": RecastRuleSet, "A2": RecastRuleSet, ...}

    has_frequency_dictionary: bool = False
    has_collocation_dictionary: bool = False
    has_native_corpus: bool = False
    alternative_data_source: str = ""
    honorifics_system: str = "none"
    register_distinction: list = field(default_factory=list)
    romanization_system: Optional[str] = None

    def get_recast_rules(self, level: str) -> RecastRuleSet:
        """Acceso seguro — si el nivel no tiene reglas propias, retorna set vacío."""
        return self.recast_by_level.get(level, RecastRuleSet())

    def get_pareto(self, level: str) -> Optional[ParetoLevel]:
        return self.pareto_by_level.get(level)


@dataclass
class GlobalRecastEngine:
    """Capa 1 — universal, una sola instancia para todo el sistema, no por idioma."""
    red_label: str
    red_definition: str
    red_action: str
    amber_label: str
    amber_definition: str
    amber_action: str
    green_label: str
    green_definition: str
    green_action: str