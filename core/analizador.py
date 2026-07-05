# core/analizador.py
import re
import json
import logging
from dataclasses import dataclass
from typing import Optional
import ollama
from config.settings import OLLAMA_MODEL, ANALIZADOR_TEMPERATURE
from data.db import Database
from data.models import LoraTrainingCandidate
from languages.base_manifest import LanguageManifest, GlobalRecastEngine

logger = logging.getLogger(__name__)


@dataclass
class Diagnosis:
    error_detected: bool = False
    error_type: Optional[str] = None       # "red" | "amber" | "green"
    error_form: Optional[str] = None
    correct_form: Optional[str] = None
    structure: Optional[str] = None
    tema_relacionado: Optional[str] = None
    parsed_successfully: bool = True


class Analizador:
    """Módulo 1 del pipeline — diagnóstico determinista, sin RAG, sin conversación.
    Corre en cada turno, sin excepción (ADR confirmado)."""

    def __init__(self, db: Database, model: str = OLLAMA_MODEL):
        self.db = db
        self.model = model

    def diagnose(self, user_input: str, level: str,
                 manifest: LanguageManifest, global_recast: GlobalRecastEngine,
                 history_context: str = "") -> Diagnosis:

        system_prompt = self._build_prompt(level, manifest, global_recast)
        user_message = self._build_user_message(user_input, history_context)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                options={"temperature": ANALIZADOR_TEMPERATURE}
            )
            raw = response["message"]["content"]
        except Exception as e:
            logger.error(f"Analizador LLM call failed: {e}")
            raise

        diagnosis = self._parse_response(raw)

        # Captura para LoRA — fila separada del Conversador
        self.db.log_lora_candidate(LoraTrainingCandidate(
            module="analizador",
            full_prompt=f"{system_prompt}\n---\n{user_message}",
            raw_output=raw,
            parsed_successfully=diagnosis.parsed_successfully,
            validation_source="auto" if diagnosis.parsed_successfully else None
        ))

        return diagnosis

    def _build_prompt(self, level: str, manifest: LanguageManifest,
                    global_recast: GlobalRecastEngine) -> str:
        rules = manifest.get_recast_rules(level)

        red_list = "\n  - ".join(rules.red) if rules.red else "(no specific rules for this level)"
        amber_list = "\n  - ".join(rules.amber) if rules.amber else "(none)"
        green_list = "\n  - ".join(rules.green) if rules.green else "(none)"

        return f"""You are a deterministic linguistic analyzer. Your only function is to diagnose errors.
    You NEVER converse, NEVER generate natural language responses.

    SEVERITY DEFINITIONS:
    RED: The error prevents comprehension, radically changes meaning, or affects a structure explicitly marked as Active Pareto for the student's current level.
    AMBER: The error does not break communication but sounds foreign, or the student has made the same error 2+ times in the session.
    GREEN: The error belongs to a morphological or pragmatic structure above the student's current level, or is an accent/dialect variation that does not affect intelligibility.

    LANGUAGE: {manifest.language_name} | LEVEL: {level}

    RED (always flag):
    - {red_list}

    AMBER (flag if pattern, not isolated error):
    - {amber_list}

    GREEN (ignore — do not flag):
    - {green_list}

    OUTPUT FORMAT — respond ONLY with this JSON, no additional text:
    {{"error_detected": true|false, "error_type": "red"|"amber"|"green"|null, "error_form": "...", "correct_form": "...", "structure": "...", "tema_relacionado": "..."}}

    "tema_relacionado" must be a brief keyword about the grammatical topic of the error (e.g. "locative_case", "verbal_aspect", "verb_byc").
    If no error, all fields except error_detected must be null.

    CRITICAL: Output must be valid JSON and nothing else. No comments, no reasoning."""

    def _parse_response(self, raw: str) -> Diagnosis:
        # Tolerante a texto extra antes/después del JSON
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)

        if not json_match:
            logger.warning(f"Analizador: no se encontró JSON en la respuesta: {raw[:200]}")
            return Diagnosis(parsed_successfully=False)

        try:
            data = json.loads(json_match.group(0))
            return Diagnosis(
                error_detected=data.get("error_detected", False),
                error_type=data.get("error_type"),
                error_form=data.get("error_form"),
                correct_form=data.get("correct_form"),
                structure=data.get("structure"),
                tema_relacionado=data.get("tema_relacionado"),
                parsed_successfully=True
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Analizador: JSON malformado: {e} — raw: {raw[:200]}")
            return Diagnosis(parsed_successfully=False)
        
    def _build_user_message(self, user_input: str, history_context: str) -> str:
        context_section = f"\nRecent conversation context:\n{history_context}\n" if history_context else ""
        return f"""{context_section}
    User input to analyze:
    "{user_input}"

    Diagnose this text according to the rules provided."""