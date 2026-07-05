# modules/drill_generator.py
import yaml
import random
import logging
from pathlib import Path
from dataclasses import dataclass
from languages.base_manifest import LanguageManifest
from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

DRILLS_DIR = BASE_DIR / "languages" / "drills"


@dataclass
class DrillSet:
    structure: str
    sentences: list[str]
    level: str


class DrillGenerator:
    """Generates structural permutations from YAML drill definitions.
    Zero LLM calls — pure Python. Triggered by Analizador red error."""

    def __init__(self, manifest: LanguageManifest):
        self.manifest = manifest
        self._cache: dict[str, dict] = {}

    def generate(self, structure: str, level: str, n: int = 3) -> DrillSet | None:
        drill_path = self.manifest.drill_mappings.get(structure)
        if not drill_path:
            logger.debug(f"No drill mapping for structure: {structure}")
            return None

        full_path = BASE_DIR / "languages" / drill_path
        drill_data = self._load(full_path)
        if not drill_data:
            return None

        sentences = self._build_sentences(drill_data, level, n)
        if not sentences:
            logger.debug(f"No sentences generated for {structure} at {level}")
            return None

        return DrillSet(structure=structure, sentences=sentences, level=level)

    def _load(self, path: Path) -> dict | None:
        str_path = str(path)
        if str_path in self._cache:
            return self._cache[str_path]
        if not path.exists():
            logger.warning(f"Drill file not found: {path}")
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self._cache[str_path] = data
        return data

    def _build_sentences(self, data: dict, level: str, n: int) -> list[str]:
        structure = data.get("structure", "")

        if structure == "verb_byc":
            return self._build_byc(data, level, n)
        elif structure == "verbal_aspect":
            return self._build_aspekt(data, level, n)
        elif structure in ("chunk_accusative", "negation_genitive"):
            return self._build_case_pairs(data, level, n)
        elif structure == "locative_case":
            return self._build_locative(data, level, n)
        else:
            logger.warning(f"Unknown drill structure type: {structure}")
            return []

    def _build_byc(self, data: dict, level: str, n: int) -> list[str]:
        template = data["template"]
        sujetos = data.get("sujetos", [])
        complementos = data.get("complementos", {}).get(level, [])
        if not sujetos or not complementos:
            return []
        selected = random.sample(
            [(s[0], s[1]) for s in sujetos],
            min(n, len(sujetos))
        )
        comps = random.sample(complementos, min(n, len(complementos)))
        return [
            template.format(sujeto=suj, verbo=verb, complemento=comp)
            for (suj, verb), comp in zip(selected, comps)
        ]

    def _build_aspekt(self, data: dict, level: str, n: int) -> list[str]:
        template = data["template"]
        pary = data.get("pary", {}).get(level, [])
        if not pary:
            return []
        selected = random.sample(pary, min(n, len(pary)))
        return [
            template.format(imperfective=p[0], perfective=p[1])
            for p in selected
        ]

    def _build_case_pairs(self, data: dict, level: str, n: int) -> list[str]:
        template_key = list(data.keys())
        pairs_key = [k for k in data.keys() if k not in
                     ("structure", "language", "niveles", "template")][0]
        template = data.get("template", "")
        pairs = data.get(pairs_key, {}).get(level, [])
        if not pairs or not template:
            return []
        selected = random.sample(pairs, min(n, len(pairs)))
        # segunda forma de cada par es el caso correcto
        return [template.replace("{" + pairs_key.rstrip("s") + "}", p[1])
                for p in selected]

    def _build_locative(self, data: dict, level: str, n: int) -> list[str]:
        level_data = data.get("pary", {}).get(level, {})
        if not level_data:
            return []
        template_acc = level_data.get("template_acc", "")
        template_loc = level_data.get("template_loc", "")
        pairs = level_data.get("pary", [])
        if not pairs:
            return []
        selected = random.sample(pairs, min(n // 2 + 1, len(pairs)))
        sentences = []
        for p in selected:
            if template_acc:
                sentences.append(template_acc.replace("{biernik}", p[0])
                                  .replace("{dopelniacz}", p[0]))
            if template_loc:
                sentences.append(template_loc.replace("{miejscownik}", p[1]))
        return sentences[:n]