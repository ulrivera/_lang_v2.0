## TECHNICAL DESIGN DOCUMENT

### Sistema de Adquisición Lingüística Pareto-Eficiente

#### v1.0 — Documento vivo

---

#### 1. REFERENCIAS

PRD de referencia: `_lang.md` v1.0 — Metodología de Adquisición Lingüística Pareto-Eficiente

Principio rector del sistema: **Carga mínima en el momento correcto.** Cada componente se inicializa solo cuando es necesario, procesa solo lo que necesita, y libera recursos inmediatamente después.

---

#### 2. ARCHITECTURE DECISION RECORDS

Decisiones tomadas e inamovibles sin consenso explícito del equipo:

|ID|Decisión|Alternativa descartada|Razón|
|---|---|---|---|
|ADR-001|LLM: Qwen 2.5 7B Instruct Q4_K_M via Ollama|Llama 3.1 8B, Phi-3 mini|Mejor cobertura multilingüe, especialmente asiático. Phi-3 descartado por inconsistencia en rol pedagógico|
|ADR-002|TTS: edge-tts, motor único|pyttsx3 + Kokoro + fallback|Simplicidad arquitectónica. Calidad suficiente. pl-PL-MarekNeural / ZofiaNeural como prioridad|
|ADR-003|STT: faster-whisper small|whisper original, medium|Balance velocidad/precisión en M1 16GB. Flag especial para lenguas tonales|
|ADR-004|Audio: FFmpeg|librosa, pydub|Madurez, performance, control fino de pausas y velocidad|
|ADR-005|BD: SQLite WAL mode|PostgreSQL, archivos YAML|Uso personal local, sin concurrencia real, zero dependencies|
|ADR-006|UI: CLI desacoplada del Core|CLI acoplada|Migración futura a GUI sin reescritura. Contrato abstracto desde día 1|
|ADR-007|Extensión de idiomas: manifiestos YAML|hardcoding, subclases por idioma|Open/Closed Principle — nuevos idiomas sin tocar el motor|
|ADR-008|Prompts: Context Stack 4 capas|prompt único, prompt dinámico|Eficiencia: Capas 1-2 se compilan una vez, Capas 3-4 por sesión|
| ADR-009 | Recast: LLM detecta + JSON estructurado | Detector Python puro | Morfología eslava hace inviable regex sin parser morfológico completo |
| ADR-010 | Nivel: umbral errores rojos en N sesiones consecutivas | SRS dominado | Simple, auditable, el usuario confirma siempre |
| ADR-011 | Recast inline, parafraseo, nunca eco, todas las modalidades | Recast marcado explícito | Protege flujo conversacional y filtro afectivo |
| ADR-012 | Romanización configurable por nivel (A2=on, B2=toggle, C2=off) | Siempre visible / siempre oculta | Reduce andamiaje progresivamente alineado con Pareto |
---

#### 3. ESTRUCTURA DEL PROYECTO

```
lang/
├── core/
│   ├── engine.py              # Orquestador principal del sistema
│   ├── context_stack.py       # Compilador y gestor de las 4 capas de prompt
│   ├── session_manager.py     # Ciclo de vida de sesión: abrir, cerrar, resumir
│   ├── recast_engine.py       # Semáforo de errores + lógica de reformulación
│   └── srs_engine.py          # Scheduler SM-2, micro-sesiones de recuperación
│
├── modules/
│   ├── practice/
│   │   ├── base_practice.py   # Clase abstracta común a las 4 modalidades
│   │   ├── chat_chat.py
│   │   ├── chat_audio.py
│   │   ├── audio_chat.py
│   │   └── audio_audio.py
│   ├── passive_studio.py      # Generación audio desde resúmenes de sesión
│   └── audio_obsidian.py      # Generación audio desde notas Obsidian
│
├── audio/
│   ├── tts.py                 # Wrapper edge-tts asíncrono
│   ├── stt.py                 # Wrapper faster-whisper, flag tonal
│   └── processor.py           # FFmpeg: pausas, velocidad, normalización
│
├── data/
│   ├── db.py                  # SQLite interface, queries centralizados
│   ├── models.py              # Dataclasses: Session, SRSItem, FineTuningLog
│   └── obsidian_parser.py     # Stub en Sprint 1, implementación en Sprint 5
│
├── languages/
│   ├── base_manifest.py       # Clase abstracta LanguageManifest
│   ├── loader.py              # YAML → objeto LanguageManifest validado
│   └── manifests/
│       ├── pl_manifest.yaml   # Prioridad Sprint 2
│       ├── en_manifest.yaml
│       ├── zh_manifest.yaml
│       ├── ja_manifest.yaml
│       ├── vi_manifest.yaml
│       ├── id_manifest.yaml
│       └── fr_manifest.yaml
│
├── interface/
│   ├── base_interface.py      # Contrato abstracto — nunca cambia
│   ├── cli.py                 # Implementación actual
│   └── gui/                   # Vacío ahora, existe para señalizar intención
│
├── config/
│   └── settings.py            # Paths, parámetros globales, constantes
│
└── tests/
    ├── test_context_stack.py
    ├── test_srs_engine.py
    ├── test_recast_engine.py
    ├── test_audio_pipeline.py
    └── test_manifest_loader.py
```

---

#### 4. JERARQUÍA DE CLASES — CONTRATOS OOP

Regla: ninguna clase concreta importa otra clase concreta directamente. Todo depende de abstracciones.

```
BaseInterface (ABC)
└── CLI
└── GUI (futuro)

LanguageManifest (ABC)
└── LoadedManifest (generado por loader.py desde YAML)

BasePractice (ABC)
├── ChatChat
├── ChatAudio
├── AudioChat
└── AudioAudio

BaseAudioProcessor (ABC)
├── TTSProcessor (edge-tts)
├── STTProcessor (faster-whisper)
└── FFmpegProcessor

BaseModule (ABC)
├── PracticeModule
├── PassiveStudioModule
└── AudioObsidianModule
```

El `Engine` solo conoce las clases abstractas. Nunca instancia concreciones directamente — usa un `ServiceLocator` o inyección de dependencias simple.

---

#### 5. CONTEXT STACK — ESPECIFICACIÓN

Las 4 capas se compilan en texto y se concatenan antes de cada llamada al LLM. Las Capas 1 y 2 se compilan al arrancar el sistema. Las Capas 3 y 4 se recompilan al cambiar idioma o abrir sesión respectivamente.

**Capa 1 — Identidad del tutor (permanente)**  
Define personalidad, reglas globales de comportamiento, lo que nunca cambia independientemente del idioma o nivel.

**Capa 2 — Nivel MCER (por nivel)**  
Define umbrales de corrección, densidad de vocabulario esperada, criterios de progresión. Cambia cuando el usuario sube de nivel.

**Capa 3 — Manifiesto del idioma (por idioma)**  
Morfología, cuellos de botella tipológicos, zona roja específica, patrones de drill, registro sociolingüístico. Viene del YAML.

**Capa 4 — Contexto operativo de sesión (por sesión)**  
Modalidad activa, gancho de sesión anterior, tags Obsidian activos, contador de errores repetidos en sesión actual.

Tamaño máximo por capa para no saturar contexto del modelo:

- Capa 1: ~300 tokens
- Capa 2: ~200 tokens
- Capa 3: ~400 tokens
- Capa 4: ~200 tokens
- Total overhead de contexto: ~1100 tokens por llamada

---

#### 6. SCHEMA DE BASE DE DATOS

sql

```sql
-- Sesiones
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    language TEXT NOT NULL,
    level TEXT NOT NULL,          -- A2, B2, C2
    modality TEXT NOT NULL,       -- chat_chat, chat_audio, audio_chat, audio_audio
    duration_seconds INTEGER,
    summary TEXT,                 -- generado por LLM al cerrar sesión
    hook_next_session TEXT,       -- gancho para próxima sesión, generado por LLM
    created_at TEXT DEFAULT (datetime('now'))
);

-- Ítems producidos en sesión
CREATE TABLE session_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    item_type TEXT NOT NULL,      -- vocab, collocation, chunk, grammar
    form TEXT NOT NULL,           -- la forma producida por el usuario
    correct INTEGER NOT NULL,     -- 1 correcto, 0 incorrecto
    error_type TEXT,              -- red, amber, green
    recast_applied TEXT           -- cómo respondió el tutor
);

-- SRS
CREATE TABLE srs_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    item TEXT NOT NULL,
    translation TEXT,
    item_type TEXT,               -- vocab, collocation, chunk
    ease_factor REAL DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    last_quality INTEGER,         -- 0-5 escala SM-2
    next_review TEXT,
    source TEXT,                  -- session_id o manifest
    created_at TEXT DEFAULT (datetime('now'))
);

-- Audio generado
CREATE TABLE passive_audio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    source_module TEXT NOT NULL,  -- passive_studio, audio_obsidian
    file_path TEXT NOT NULL,
    items_targeted TEXT,          -- JSON array de ítems objetivo
    duration_seconds INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Datos para finetuning futuro
CREATE TABLE finetuning_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_item_id INTEGER REFERENCES session_items(id),
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    user_input TEXT NOT NULL,
    ideal_output TEXT NOT NULL,   -- el recast aplicado
    error_type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

#### 7. CONTRATO DEL MANIFIESTO YAML

Todo manifiesto debe implementar estos campos. El `loader.py` valida contra este schema antes de cargar.

yaml

```yaml
# CAMPOS OBLIGATORIOS
language_code: "pl"
language_name: "Polish"
family: "slavic_inflectional"
tonal: false

tts:
  engine: "edge-tts"
  voices:
    primary: "pl-PL-MarekNeural"
    secondary: "pl-PL-ZofiaNeural"

stt:
  tonal_correction: false

morphology:
  bottleneck: ""           # descripción del cuello de botella tipológico
  red_zone_structures: []  # lista de estructuras siempre en zona roja
  drill_patterns: []       # patrones de drill con template

pareto:
  A2:
    word_families: 0
    source_corpus: ""
  B2:
    word_families: 0
    collocations_priority: ""
    source_corpus: ""
  C2:
    focus: ""
    source_corpus: ""

correction_rules:
  red_zone: []
  amber_zone: []
  green_zone: []

resources:
  has_frequency_dictionary: false
  has_collocation_dictionary: false
  has_native_corpus: false
  alternative_data_source: ""

# CAMPOS OPCIONALES
pragmatics:
  honorifics_system: "none"
  register_distinction: []
```

---

#### 8. BACKLOG — SPRINT 0 AL 5

**Sprint 0 — Fundación técnica**  
No produce features visibles. Produce la base sin la cual nada funciona.

- Inicializar repositorio Git con estructura de carpetas completa
- `settings.py` con paths y constantes
- `models.py` con dataclasses de Session, SRSItem, FineTuningLog
- `db.py` con schema SQL y métodos CRUD básicos
- `base_manifest.py` clase abstracta
- `loader.py` carga y valida YAML contra schema
- `base_interface.py` contrato abstracto de UI
- `cli.py` skeleton que arranca sin errores
- Tests de BD y loader

Criterio de salida del sprint: el sistema arranca, crea la BD, carga un manifiesto YAML de prueba, y muestra un menú vacío en CLI.

**Sprint 1 — Context Stack + LLM**

- `context_stack.py` compilador de 4 capas
- Conexión Ollama + wrapper de llamada
- `session_manager.py` abrir y cerrar sesión
- `pl_manifest.yaml` completo
- `chat_chat.py` primera modalidad funcional con recast básico
- Generación de summary y hook al cerrar sesión

Criterio de salida: conversación real en polaco chat-chat con recast funcionando.

**Sprint 2 — Recast Engine + SRS**

- `recast_engine.py` semáforo completo rojo/ámbar/verde
- `srs_engine.py` SM-2 scheduler
- Micro-sesiones de recuperación
- `session_items` poblándose correctamente
- `finetuning_log` capturando pares input/recast

Criterio de salida: el sistema recuerda errores entre sesiones y programa revisiones.

**Sprint 3 — Audio pipeline**

- `tts.py` wrapper edge-tts asíncrono
- `stt.py` wrapper faster-whisper
- `processor.py` FFmpeg con pausas de saliencia
- Modalidades `chat_audio`, `audio_chat`, `audio_audio`

Criterio de salida: conversación completa en modalidad audio-audio en polaco.

**Sprint 4 — Passive Studio**

- `passive_studio.py` generador de texto desde resúmenes
- Marcadores de saliencia automáticos con formato `[objetivo]...[/objetivo]`
- Pipeline completo → mp3 etiquetado con metadata

Criterio de salida: el sistema genera un mp3 de 5 minutos basado en la última sesión.

**Sprint 5 — Audio Obsidian + manifiestos restantes**

- `obsidian_parser.py` implementación real desde stub
- TF-IDF sobre notas del vault
- `audio_obsidian.py` pipeline completo
- Manifiestos EN, ZH, JA, VI, ID, FR

Criterio de salida: sistema completo operativo en los 7 idiomas.

---

#### 9. CONVENCIONES DE CÓDIGO

- Python 3.11+
- Type hints en todas las funciones
- Docstrings en todas las clases públicas
- Sin prints en Core Engine — solo en Interface Layer
- Logging con módulo `logging` estándar, nivel DEBUG en desarrollo
- Commits en inglés, presentes: `add`, `fix`, `refactor`, `test`

---

#### 10. DEUDA TÉCNICA CONOCIDA Y ACEPTADA

Decisiones conscientes que se revisarán en versiones futuras:

- `ObsidianParser` es stub hasta Sprint 5 — aceptado
- Validación semántica de producción del usuario es regex hasta Sprint 2, LLM después
- Sin autenticación ni cifrado — proyecto personal local
- GUI pospuesta indefinidamente — arquitectura preparada pero no implementada
- Manifiestos de idiomas asiáticos sin validación nativa de tonos en STT
- Tests de Engine requieren Ollama activo — pendiente mock para CI

---

Este es el documento que vive en la raíz del repositorio como `TECHNICAL_DESIGN.md`. Se actualiza cada vez que se toma una decisión de arquitectura nueva. Nunca se edita para reflejar lo que ya fue implementado — eso es trabajo del `CHANGELOG.md`.