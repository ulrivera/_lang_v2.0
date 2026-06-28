# languages/loader.py
import yaml
import logging
from pathlib import Path
from languages.base_manifest import (
    LanguageManifest, TTSConfig, MorphologyConfig, ParetoLevel
)
from config.settings import MANIFESTS_DIR

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "language_code", "language_name", "family",
    "tonal", "tts", "morphology", "pareto", "correction_rules"
]


class ManifestLoader:
    def load(self, language_code: str) -> LanguageManifest:
        path = MANIFESTS_DIR / f"{language_code}_manifest.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._validate(data, path)
        return self._parse(data)

    def _validate(self, data: dict, path: Path) -> None:
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            raise ValueError(f"Manifest {path.name} missing fields: {missing}")

    def _parse(self, d: dict) -> LanguageManifest:
        tts_data = d["tts"]
        voices = tts_data.get("voices", {})

        return LanguageManifest(
            language_code=d["language_code"],
            language_name=d["language_name"],
            family=d["family"],
            tonal=d["tonal"],
            tts=TTSConfig(
                engine=tts_data["engine"],
                primary_voice=voices.get("primary", ""),
                secondary_voice=voices.get("secondary")
            ),
            morphology=MorphologyConfig(
                bottleneck=d["morphology"].get("bottleneck", ""),
                red_zone_structures=d["morphology"].get("red_zone_structures", []),
                drill_patterns=d["morphology"].get("drill_patterns", [])
            ),
            pareto_A2=ParetoLevel(**d["pareto"]["A2"]),
            pareto_B2=ParetoLevel(**d["pareto"]["B2"]),
            pareto_C2=ParetoLevel(**d["pareto"]["C2"]),
            correction_red=d["correction_rules"].get("red_zone", []),
            correction_amber=d["correction_rules"].get("amber_zone", []),
            correction_green=d["correction_rules"].get("green_zone", []),
            has_frequency_dictionary=d.get("resources", {}).get("has_frequency_dictionary", False),
            has_collocation_dictionary=d.get("resources", {}).get("has_collocation_dictionary", False),
            has_native_corpus=d.get("resources", {}).get("has_native_corpus", False),
            alternative_data_source=d.get("resources", {}).get("alternative_data_source", ""),
            honorifics_system=d.get("pragmatics", {}).get("honorifics_system", "none"),
            register_distinction=d.get("pragmatics", {}).get("register_distinction", [])
        )