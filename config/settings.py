# config/settings.py
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Datos
DB_PATH = BASE_DIR / "data" / "lang2.db"
AUDIO_OUTPUT_DIR = BASE_DIR / "audio_output"
LOGS_DIR = BASE_DIR / "logs"
CHROMA_DIR = BASE_DIR / "chroma_db"

AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

# Manifiestos
MANIFESTS_DIR = BASE_DIR / "languages" / "manifests"

# Vault de Obsidian — fuente del RAG
VAULT_BASE_PATH = Path("/Users/raulrivera/Desktop/3-Languages")

# Embeddings
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Chunking (PRD v2.0 sección 4.1)
CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_RATIO = 0.125  # punto medio de 10-15%

# LLM
OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
OLLAMA_BASE_URL = "http://localhost:11434"

# Temperaturas por módulo (PRD v2.0 sección 5.1)
ANALIZADOR_TEMPERATURE = 0.1   # determinista — solo diagnóstico
CONVERSADOR_TEMPERATURE = 0.7  # natural — generación conversacional

# STT
WHISPER_MODEL_SIZE = "small"

# Sesión
MAX_SESSION_DURATION_SECONDS = 3600
MAX_HISTORY_TURNS = 6

# Niveles MCER soportados (PRD v2.0 añade A0)
SUPPORTED_LEVELS = ["A0", "A2", "B2", "C2"]

# Romanización por nivel
ROMANIZATION_BY_LEVEL = {
    "A0": "always",
    "A2": "always",
    "B2": "toggle",
    "C2": "off"
}

# Logging
LOG_LEVEL = "DEBUG"

# Mapeo carpeta del vault → código ISO del idioma
VAULT_LANGUAGE_FOLDERS = {
    "polski": "pl",
    # futuro: "ingles": "en", "mandarin": "zh", etc.
}