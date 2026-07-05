# core/conversador.py
import logging
from dataclasses import dataclass
import ollama
from config.settings import OLLAMA_MODEL, CONVERSADOR_TEMPERATURE, MAX_HISTORY_TURNS
from data.db import Database
from data.models import LoraTrainingCandidate
from core.analizador import Diagnosis
from languages.base_manifest import LanguageManifest, GlobalRecastEngine
from modules.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class ConversadorResponse:
    text: str
    rag_chunks_used: int = 0
    parsed_successfully: bool = True


class Conversador:
    """Módulo 2 del pipeline — genera respuesta natural con contexto RAG.
    Recibe el diagnóstico del Analizador, nunca detecta errores por sí mismo."""

    def __init__(self, db: Database, vector_store: VectorStore, model: str = OLLAMA_MODEL):
        self.db = db
        self.vector_store = vector_store
        self.model = model

    def respond(self, user_input: str, diagnosis: Diagnosis, level: str,
                user_l1: str, manifest: LanguageManifest,
                global_recast: GlobalRecastEngine,
                history: list[dict]) -> ConversadorResponse:

        rag_results = self._query_rag(user_input, diagnosis, level, manifest.language_code)
        system_prompt = self._build_prompt(level, user_l1, manifest, global_recast, rag_results, diagnosis)
        history_for_llm = history[-MAX_HISTORY_TURNS:]

        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history_for_llm)
            messages.append({"role": "user", "content": user_input})

            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={"temperature": CONVERSADOR_TEMPERATURE}
            )
            raw = response["message"]["content"]
        except Exception as e:
            logger.error(f"Conversador LLM call failed: {e}")
            raise

        self.db.log_lora_candidate(LoraTrainingCandidate(
            module="conversador",
            full_prompt=f"{system_prompt}\n---\nUSER: {user_input}",
            raw_output=raw,
            parsed_successfully=True,
            validation_source="auto"
        ))

        return ConversadorResponse(
            text=raw.strip(),
            rag_chunks_used=len(rag_results)
        )

    def _query_rag(self, user_input: str, diagnosis: Diagnosis,
                   level: str, language_code: str) -> list[dict]:
        results = []

        # Query 1 — contenido semántico del turno del usuario
        semantic_results = self.vector_store.query(
            query_text=user_input,
            nivel=level,
            language=language_code,
            n_results=3
        )
        results.extend(semantic_results)

        # Query 2 — tema relacionado al error (si hay diagnóstico)
        if diagnosis.error_detected and diagnosis.tema_relacionado:
            error_results = self.vector_store.query(
                query_text=diagnosis.tema_relacionado,
                nivel=level,
                language=language_code,
                n_results=2
            )
            # Evitar duplicados por chunk_id
            existing_texts = {r["text"] for r in results}
            for r in error_results:
                if r["text"] not in existing_texts:
                    results.append(r)

        return results

    def _build_prompt(self, level: str, user_l1: str,
                    manifest: LanguageManifest, global_recast: GlobalRecastEngine,
                    rag_results: list[dict], diagnosis: Diagnosis) -> str:

        rag_section = self._format_rag_context(rag_results)
        diagnosis_section = self._format_diagnosis(diagnosis)

        return f"""LANGUAGE LOCK: {manifest.language_name} ONLY.
    You must respond exclusively in {manifest.language_name}.
    Never mix scripts, characters, or words from any other language — not even a single word.
    If you detect yourself writing in another language, stop and rewrite entirely in {manifest.language_name}.

    You are a conversational language tutor for {manifest.language_name}.
    The student's base language (L1) is {user_l1}. Always respond in {manifest.language_name}.

    CORRECTION TECHNIQUE — NATURAL PARAPHRASE ONLY:
    When an error is detected, use it as a conversational springboard.
    NEVER say: "You should say X" / "The correct form is X" / "Error: X"
    ALWAYS: use the correct form naturally inside your next question or comment.

    Correct paraphrase example:
    - Student says: "ten dnia jest gorąco"
    - Tutor responds: "Tak, tego dnia jest naprawdę gorąco! Lubisz taką pogodę, czy wolisz chłodniejsze dni?"
    → incorporates "tego dnia" naturally inside a question that advances the conversation

    Incorrect examples:
    - "Ten dnia jest gorąco." (only capitalizes — NOT a paraphrase)
    - "Popraw: tego dnia" (explicitly flags the error — FORBIDDEN)

    SEVERITY RULES:
    RED: incorporate correct form naturally, advance conversation.
    AMBER: model correct form implicitly in your response.
    GREEN: ignore completely, validate message and continue.

    CURRENT LEVEL: {level}

    {diagnosis_section}

    {rag_section}

    Continue the conversation naturally in {manifest.language_name}, incorporating support material only if relevant."""

    def _format_diagnosis(self, diagnosis: Diagnosis) -> str:
        if not diagnosis.error_detected:
            return "DIAGNOSIS: No errors detected in this turn."
        return f"""ANALYZER DIAGNOSIS:
    - Severity: {diagnosis.error_type.upper()}
    - Incorrect form: {diagnosis.error_form}
    - Correct form: {diagnosis.correct_form}
    - Structure: {diagnosis.structure}
    - Required action: incorporate "{diagnosis.correct_form}" naturally in your response."""


    def _format_rag_context(self, results: list[dict]) -> str:
        if not results:
            return "SUPPORT MATERIAL: No relevant cards retrieved for this turn."

        chunks_text = "\n---\n".join(
            f"[{r['metadata'].get('tipo','').upper()} — {r['metadata'].get('tema','')}]\n{r['text']}"
            for r in results
        )
        return f"SUPPORT MATERIAL (from user vault, level ≤ {results[0]['metadata'].get('nivel','')}):\n{chunks_text}"