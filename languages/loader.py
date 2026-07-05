# languages/loader.py
import yaml
import logging
from pathlib import Path
from languages.base_manifest import (
    LanguageManifest, TTSConfig, MorphologyConfig, ParetoLevel,
    RecastRuleSet, GlobalRecastEngine
)
from config.settings import MANIFESTS_DIR, BASE_DIR

logger = logging.getLogger(__name__)

REQUIRED_MANIFEST_FIELDS = [
    "language_code", "language_name", "family", "tonal"
]

GLOBAL_RECAST_PATH = BASE_DIR / "languages" / "recast_global.yaml"


class ManifestLoader:

    def load_global_recast(self) -> GlobalRecastEngine:
        """Carga la Capa 1 — se llama una sola vez al iniciar el sistema."""
        if not GLOBAL_RECAST_PATH.exists():
            raise FileNotFoundError(f"Global recast config not found: {GLOBAL_RECAST_PATH}")

        with open(GLOBAL_RECAST_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return GlobalRecastEngine(
            red_label=data["red"]["label"],
            red_definition=data["red"]["definition"].strip(),
            red_action=data["red"]["action"],
            amber_label=data["amber"]["label"],
            amber_definition=data["amber"]["definition"].strip(),
            amber_action=data["amber"]["action"],
            green_label=data["green"]["label"],
            green_definition=data["green"]["definition"].strip(),
            green_action=data["green"]["action"],
        )

    def load(self, language_code: str) -> LanguageManifest:
        """Carga el manifiesto completo de un idioma — Capa 2."""
        manifest_path = MANIFESTS_DIR / f"{language_code}_manifest.yaml"
        recast_path = MANIFESTS_DIR / f"{language_code}_recast.yaml"

        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        if not recast_path.exists():
            raise FileNotFoundError(f"Recast file not found: {recast_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)
        with open(recast_path, "r", encoding="utf-8") as f:
            recast_data = yaml.safe_load(f)

        self._validate(manifest_data, manifest_path)
        return self._parse(manifest_data, recast_data)

    def _validate(self, data: dict, path: Path) -> None:
        missing = [f for f in REQUIRED_MANIFEST_FIELDS if f not in data]
        if missing:
            raise ValueError(f"Manifest {path.name} missing fields: {missing}")

    def _parse(self, manifest_data: dict, recast_data: dict) -> LanguageManifest:
        tts_data = manifest_data.get("tts", {})
        voices = tts_data.get("voices", {})

        # Pareto por nivel — dict dinámico, soporta cualquier subconjunto de A0-C2
        pareto_by_level = {}
        for level, level_data in manifest_data.get("pareto", {}).items():
            pareto_by_level[level] = ParetoLevel(**level_data)

        # Recast por nivel — viene del archivo {idioma}_recast.yaml
        recast_by_level = {}
        for level, rules in recast_data.get("recast_rules", {}).items():
            recast_by_level[level] = RecastRuleSet(
                red=rules.get("red", []),
                amber=rules.get("amber", []),
                green=rules.get("green", [])
            )

        return LanguageManifest(
            language_code=manifest_data["language_code"],
            language_name=manifest_data["language_name"],
            family=manifest_data.get("family", ""),
            tonal=manifest_data.get("tonal", False),
            tts=TTSConfig(
                engine=tts_data.get("engine", ""),
                primary_voice=voices.get("primary", ""),
                secondary_voice=voices.get("secondary")
            ),
            morphology=MorphologyConfig(
                bottleneck=manifest_data.get("morphology", {}).get("bottleneck", ""),
                red_zone_structures=manifest_data.get("morphology", {}).get("red_zone_structures", []),
                drill_patterns=manifest_data.get("morphology", {}).get("drill_patterns", [])
            ),
            pareto_by_level=pareto_by_level,
            recast_by_level=recast_by_level,
            has_frequency_dictionary=manifest_data.get("resources", {}).get("has_frequency_dictionary", False),
            has_collocation_dictionary=manifest_data.get("resources", {}).get("has_collocation_dictionary", False),
            has_native_corpus=manifest_data.get("resources", {}).get("has_native_corpus", False),
            alternative_data_source=manifest_data.get("resources", {}).get("alternative_data_source", ""),
            honorifics_system=manifest_data.get("pragmatics", {}).get("honorifics_system", "none"),
            register_distinction=manifest_data.get("pragmatics", {}).get("register_distinction", []),
            romanization_system=manifest_data.get("romanization_system")
        )