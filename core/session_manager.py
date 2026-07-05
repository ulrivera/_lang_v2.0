# core/session_manager.py
import logging
from datetime import datetime
from typing import Optional
from core.analizador import Analizador, Diagnosis
from core.conversador import Conversador, ConversadorResponse
from data.db import Database
from data.models import Session, SessionItem, FineTuningLog
from languages.base_manifest import LanguageManifest, GlobalRecastEngine
from languages.loader import ManifestLoader
from config.settings import ROMANIZATION_BY_LEVEL
from modules.drill_generator import DrillGenerator, DrillSet

logger = logging.getLogger(__name__)


class SessionManager:

    def __init__(self, db: Database, analizador: Analizador,
                 conversador: Conversador, manifest: LanguageManifest,
                 global_recast: GlobalRecastEngine):
        self.db = db
        self.analizador = analizador
        self.conversador = conversador
        self.manifest = manifest
        self.global_recast = global_recast

        self._session: Optional[Session] = None
        self._session_id: Optional[int] = None
        self._history: list[dict] = []
        self._start_time: Optional[datetime] = None
        self._amber_tracker: dict[str, int] = {}

        self.drill_generator = DrillGenerator(manifest)

    def open(self, level: str, modality: str, user_l1: str) -> str:
        last = self.db.get_last_session(self.manifest.language_code)
        hook = last["hook_next_session"] if last and last["hook_next_session"] else ""

        romanization_rule = ROMANIZATION_BY_LEVEL.get(level, "off")
        romanization_active = romanization_rule == "always"

        self._session = Session(
            language=self.manifest.language_code,
            level=level,
            modality=modality,
            user_l1=user_l1,
            romanization_active=romanization_active
        )
        self._session_id = self.db.create_session(self._session)
        self._start_time = datetime.now()
        self._history = []
        self._amber_tracker = {}

        logger.info(f"Session opened — {self.manifest.language_code} / {level} / {modality}")

        # Apertura: el Conversador abre sin diagnóstico
        opening = self.conversador.respond(
            user_input=f"[INICIO DE SESIÓN — abre con este gancho de forma natural: {hook}]" if hook else "[INICIO DE SESIÓN — abre la conversación de forma natural]",
            diagnosis=Diagnosis(),
            level=level,
            user_l1=user_l1,
            manifest=self.manifest,
            global_recast=self.global_recast,
            history=[]
        )

        self._history.append({"role": "assistant", "content": opening.text})
        return opening.text

    def turn(self, user_input: str) -> tuple[ConversadorResponse, Diagnosis]:
        if not self._session_id:
            raise RuntimeError("No active session. Call open() first.")

        level = self._session.level
        user_l1 = self._session.user_l1

        # Paso 1 — Analizador
        history_context = self._build_history_context()
        diagnosis = self.analizador.diagnose(
            user_input=user_input,
            level=level,
            manifest=self.manifest,
            global_recast=self.global_recast,
            history_context=history_context
        )

        # Escalado ámbar → rojo por repetición
        if diagnosis.error_detected and diagnosis.error_type == "amber":
            key = diagnosis.structure or diagnosis.error_form
            self._amber_tracker[key] = self._amber_tracker.get(key, 0) + 1
            if self._amber_tracker[key] >= 2:
                diagnosis.error_type = "red"
                logger.debug(f"Amber escalated to red: {key}")

        # Generar drill si error rojo
        drill: DrillSet | None = None
        if diagnosis.error_detected and diagnosis.error_type == "red" and diagnosis.structure:
            drill = self.drill_generator.generate(
                structure=diagnosis.structure,
                level=level
            )
            if drill:
                logger.debug(f"Drill generated: {drill.structure} — {len(drill.sentences)} sentences")

        # Paso 2 — Conversador
        response = self.conversador.respond(
            user_input=user_input,
            diagnosis=diagnosis,
            level=level,
            user_l1=user_l1,
            manifest=self.manifest,
            global_recast=self.global_recast,
            history=self._history
        )

        # Actualizar historial completo (para summary al cierre)
        self._history.append({"role": "user", "content": user_input})
        self._history.append({"role": "assistant", "content": response.text})

        # Persistencia
        self._session.total_items += 1
        if diagnosis.error_detected and diagnosis.error_type == "red":
            self._session.red_error_count += 1
            self._persist_error(diagnosis)

        return response, diagnosis, drill

    def close(self) -> dict:
        if not self._session_id:
            raise RuntimeError("No active session.")

        duration = int((datetime.now() - self._start_time).total_seconds())

        # Summary y hook — Conversador con historial completo
        meta = self.conversador.respond(
            user_input="[FIN DE SESIÓN — responde SOLO en este formato exacto:\nSUMMARY: una oración sobre el tema y errores principales.\nHOOK: una oración para abrir la próxima sesión naturalmente.]",
            diagnosis=Diagnosis(),
            level=self._session.level,
            user_l1=self._session.user_l1,
            manifest=self.manifest,
            global_recast=self.global_recast,
            history=self._history
        )

        summary, hook = self._parse_meta(meta.text)
        self.db.close_session(self._session_id, duration, summary, hook)

        self.db._conn().execute(
            "UPDATE sessions SET red_error_count=?, total_items=? WHERE id=?",
            (self._session.red_error_count, self._session.total_items, self._session_id)
        )
        self.db._conn().commit()

        stats = {
            "duration_seconds": duration,
            "total_items": self._session.total_items,
            "red_errors": self._session.red_error_count,
            "summary": summary,
            "hook": hook
        }
        logger.info(f"Session closed — {stats}")
        self._session_id = None
        return stats

    def _build_history_context(self) -> str:
        """Últimos 4 turnos como texto plano para el Analizador."""
        recent = self._history[-4:]
        return "\n".join(
            f"{'Usuario' if m['role'] == 'user' else 'Tutor'}: {m['content']}"
            for m in recent
        )

    def _persist_error(self, diagnosis: Diagnosis) -> None:
        item = SessionItem(
            session_id=self._session_id,
            item_type="grammar",
            form=diagnosis.error_form or "",
            correct=False,
            error_type=diagnosis.error_type,
            recast_applied=diagnosis.correct_form,
            error_form=diagnosis.error_form,
            correct_form=diagnosis.correct_form,
            structure=diagnosis.structure
        )
        item_id = self.db.add_session_item(item)

        if diagnosis.error_form and diagnosis.correct_form:
            self.db.add_finetuning_log(FineTuningLog(
                session_item_id=item_id,
                language=self.manifest.language_code,
                level=self._session.level,
                user_input=diagnosis.error_form,
                ideal_output=diagnosis.correct_form,
                error_type=diagnosis.error_type
            ))

    def _parse_meta(self, raw: str) -> tuple[str, str]:
        summary, hook = "", ""
        for line in raw.splitlines():
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("HOOK:"):
                hook = line.replace("HOOK:", "").strip()
        return summary or raw[:200], hook