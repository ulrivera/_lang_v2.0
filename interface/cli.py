# interface/cli.py
import logging
from interface.base_interface import BaseInterface
from core.analizador import Analizador
from core.conversador import Conversador
from core.session_manager import SessionManager
from modules.rag.vault_parser import VaultParser
from modules.rag.vector_store import VectorStore
from languages.loader import ManifestLoader
from data.db import Database

logger = logging.getLogger(__name__)

EXIT_COMMANDS = {"quit", "exit", "salir", "koniec", "/q", "q"}
LEVELS = {"1": "A0", "2": "A2", "3": "B2", "4": "C2"}
LANGUAGES = {"1": ("pl", "polski")}


class CLI(BaseInterface):

    def __init__(self, db: Database):
        self.db = db
        self.loader = ManifestLoader()
        self.vector_store = VectorStore()
        self.vault_parser = VaultParser()

    def run(self) -> None:
        profile = self.db.get_or_create_profile(user_l1="es", default_level="A0")
        self.display_message(f"\n=== LANG v2.0 === L1: {profile['user_l1']} / Nivel actual: {profile['current_level']}\n")

        while True:
            choice = self.display_menu("Menú Principal", {
                "1": "Practice (chat-chat)",
                "q": "Salir"
            })
            if choice == "q":
                self.display_message("Hasta luego.")
                break
            elif choice == "1":
                self._run_practice(profile)

    def _run_practice(self, profile) -> None:
        lang_choice = self.display_menu("Idioma", {"1": "Polaco"})
        lang_code, lang_folder = LANGUAGES[lang_choice]

        level_choice = self.display_menu("Nivel", LEVELS)
        level = LEVELS[level_choice]

        try:
            manifest = self.loader.load(lang_code)
            global_recast = self.loader.load_global_recast()
        except FileNotFoundError as e:
            self.display_message(f"Error cargando manifiestos: {e}")
            return

        # Indexar vault si hay tarjetas
        try:
            cards = self.vault_parser.parse_language(lang_folder)
            chunks = []
            for card in cards:
                chunks.extend(self.vault_parser.chunk_card(card))
            if chunks:
                self.vector_store.index_chunks(chunks)
                logger.debug(f"Indexed {len(chunks)} chunks for {lang_code}")
        except Exception as e:
            logger.warning(f"Vault indexing failed (continuing without RAG): {e}")

        analizador = Analizador(db=self.db)
        conversador = Conversador(db=self.db, vector_store=self.vector_store)

        sm = SessionManager(
            db=self.db,
            analizador=analizador,
            conversador=conversador,
            manifest=manifest,
            global_recast=global_recast
        )

        self.display_message(f"\nIniciando sesión — {manifest.language_name} / {level}")
        self.display_message("Escribe 'salir' o '/q' para terminar.\n")

        opening = sm.open(level=level, modality="chat_chat", user_l1=profile["user_l1"])
        self.display_message(f"\nTutor: {opening}")

        while True:
            user_input = self.get_input("Tú")
            if user_input.lower() in EXIT_COMMANDS:
                stats = sm.close()
                self._show_stats(stats)
                break
                
            response, diagnosis, drill = sm.turn(user_input)
            self.display_message(f"\nTutor: {response.text}")

            if drill:
                print(f"\n  [DRILL — {drill.structure}]")
                for i, sentence in enumerate(drill.sentences, 1):
                    print(f"  {i}. {sentence}")

            if diagnosis.error_detected and diagnosis.error_type in ("red", "amber"):
                print(f"\n  {'✗' if diagnosis.error_type == 'red' else '~'} "
                    f"[{diagnosis.error_type.upper()}] "
                    f"{diagnosis.error_form} → {diagnosis.correct_form}")

    def _show_stats(self, stats: dict) -> None:
        m, s = divmod(stats["duration_seconds"], 60)
        total = stats["total_items"]
        red = stats["red_errors"]
        ratio = f"{red/total*100:.0f}%" if total > 0 else "N/A"
        print(f"\nSesión completada — {m}m {s}s | Errores rojos: {red}/{total} ({ratio})")
        print(f"{stats['summary']}")

    def display_message(self, message: str) -> None:
        print(message)

    def get_input(self, prompt: str) -> str:
        return input(f"\n{prompt}: ").strip()

    def display_menu(self, title: str, options: dict) -> str:
        print(f"\n{title}")
        print("─" * len(title))
        for key, label in options.items():
            print(f"  [{key}] {label}")
        valid = set(options.keys())
        while True:
            choice = input("\nElige: ").strip().lower()
            if choice in valid:
                return choice
            print(f"Elige entre: {', '.join(sorted(valid))}")