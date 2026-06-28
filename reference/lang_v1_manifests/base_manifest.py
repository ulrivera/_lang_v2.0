# languages/base_manifest.py
from abc import ABC, abstractmethod
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
class LanguageManifest:
    language_code: str
    language_name: str
    family: str
    tonal: bool
    tts: TTSConfig
    morphology: MorphologyConfig
    pareto_A2: ParetoLevel
    pareto_B2: ParetoLevel
    pareto_C2: ParetoLevel
    correction_red: list = field(default_factory=list)
    correction_amber: list = field(default_factory=list)
    correction_green: list = field(default_factory=list)
    has_frequency_dictionary: bool = False
    has_collocation_dictionary: bool = False
    has_native_corpus: bool = False
    alternative_data_source: str = ""
    honorifics_system: str = "none"
    register_distinction: list = field(default_factory=list)
    romanization_system: Optional[str] = None  # nuevo: "pinyin", "hepburn", null