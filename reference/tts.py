# audio/tts.py
import asyncio
import logging
import tempfile
from pathlib import Path
import edge_tts
from config.settings import AUDIO_OUTPUT_DIR

logger = logging.getLogger(__name__)


class TTSProcessor:
    """Wrapper asíncrono de edge-tts. Genera audio desde texto."""

    def __init__(self, voice: str):
        self.voice = voice

    def speak(self, text: str, save_path: Path = None) -> Path:
        """Convierte texto a audio. Retorna path del archivo generado."""
        return asyncio.run(self._speak_async(text, save_path))

    async def _speak_async(self, text: str, save_path: Path = None) -> Path:
        if save_path is None:
            save_path = AUDIO_OUTPUT_DIR / f"tts_{id(text)}.mp3"

        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(save_path))
        logger.debug(f"TTS generated: {save_path}")
        return save_path

    def speak_and_play(self, text: str) -> None:
        """Genera audio y lo reproduce inmediatamente."""
        path = self.speak(text)
        self._play(path)
        path.unlink(missing_ok=True)  # limpia archivo temporal

    def _play(self, path: Path) -> None:
        """Reproduce audio via afplay (nativo macOS, sin dependencias)."""
        import subprocess
        subprocess.run(["afplay", str(path)], check=True)
        logger.debug(f"Audio played: {path}")