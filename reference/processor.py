# audio/processor.py
import subprocess
import logging
from pathlib import Path
from config.settings import AUDIO_OUTPUT_DIR

logger = logging.getLogger(__name__)


class FFmpegProcessor:
    """Pipeline de procesamiento de audio via FFmpeg."""

    def add_silence(self, input_path: Path, silence_ms: int = 500) -> Path:
        """Agrega silencio al final del audio — útil para pausas de saliencia."""
        output_path = AUDIO_OUTPUT_DIR / f"processed_{input_path.stem}.mp3"
        silence_sec = silence_ms / 1000

        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", f"apad=pad_dur={silence_sec}",
            str(output_path)
        ]
        self._run(cmd)
        return output_path

    def normalize(self, input_path: Path) -> Path:
        """Normaliza volumen del audio."""
        output_path = AUDIO_OUTPUT_DIR / f"norm_{input_path.stem}.mp3"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            str(output_path)
        ]
        self._run(cmd)
        return output_path

    def adjust_speed(self, input_path: Path, speed: float = 0.85) -> Path:
        """Reduce velocidad — útil para A2 donde claridad > naturalidad."""
        output_path = AUDIO_OUTPUT_DIR / f"speed_{input_path.stem}.mp3"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", f"atempo={speed}",
            str(output_path)
        ]
        self._run(cmd)
        return output_path

    def process_for_level(self, input_path: Path, level: str) -> Path:
        """Pipeline completo adaptado al nivel del estudiante."""
        if level == "A2":
            # A2: más lento, pausa larga al final
            slowed = self.adjust_speed(input_path, speed=0.82)
            result = self.add_silence(slowed, silence_ms=700)
            slowed.unlink(missing_ok=True)
            return result
        elif level == "B2":
            # B2: velocidad natural, pausa normal
            return self.add_silence(input_path, silence_ms=400)
        else:
            # C2: velocidad natural, pausa mínima
            return self.add_silence(input_path, silence_ms=200)

    def _run(self, cmd: list) -> None:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr[-300:]}")
            raise RuntimeError(f"FFmpeg failed: {result.stderr[-200:]}")
        logger.debug(f"FFmpeg OK: {' '.join(cmd[:4])}")