# audio/stt.py
import wave
import logging
import tempfile
from pathlib import Path
import pyaudio
from faster_whisper import WhisperModel
from config.settings import WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

# Parámetros de grabación
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper opera óptimo a 16kHz


class STTProcessor:
    """Captura audio del micrófono y transcribe con faster-whisper."""

    def __init__(self, language_code: str, tonal: bool = False):
        self.language_code = language_code
        self.tonal = tonal
        self._model = None  # lazy load — no carga hasta primer uso

    def _load_model(self) -> None:
        if self._model is None:
            logger.info(f"Loading Whisper {WHISPER_MODEL_SIZE}...")
            self._model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device="cpu",
                compute_type="int8"  # óptimo para M1
            )
            logger.info("Whisper model loaded")

    def listen(self) -> str:
        """Push-to-talk: graba hasta que el usuario presiona Enter.
        Retorna el texto transcrito."""
        self._load_model()

        print("\n  [🎤 Presiona Enter para empezar a grabar...]")
        input()
        print("  [🔴 Grabando... presiona Enter para terminar]")

        audio_path = self._record()

        print("  [⏳ Transcribiendo...]")
        text = self._transcribe(audio_path)
        audio_path.unlink(missing_ok=True)

        return text

    def _record(self) -> Path:
        """Graba audio hasta que el usuario presiona Enter."""
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        frames = []
        stop_flag = {"stop": False}

        import threading

        def wait_for_enter():
            input()
            stop_flag["stop"] = True

        thread = threading.Thread(target=wait_for_enter, daemon=True)
        thread.start()

        while not stop_flag["stop"]:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        pa.terminate()

        # Guardar WAV temporal
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(pa.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))

        return Path(tmp.name)

    def _transcribe(self, audio_path: Path) -> str:
        """Transcribe el archivo de audio."""
        segments, info = self._model.transcribe(
            str(audio_path),
            language=self.language_code,
            beam_size=5,
            vad_filter=True  # filtra silencio automáticamente
        )

        text = " ".join(segment.text.strip() for segment in segments)

        if self.tonal:
            logger.debug(f"Tonal language transcription confidence check needed")

        logger.debug(f"Transcribed: {text[:100]}")
        return text.strip()