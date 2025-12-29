"""Engine de audio/TTS para ANIMATR."""

import tempfile
from pathlib import Path

from animatr.engines.base import Engine, EngineResult
from animatr.schema import AudioConfig


class AudioEngine(Engine):
    """Engine para generar audio via TTS."""

    def __init__(self) -> None:
        self._temp_dir = Path(tempfile.mkdtemp(prefix="animatr_audio_"))

    def process(self, config: AudioConfig) -> EngineResult:
        """Genera audio desde texto usando el provider configurado."""
        if config.provider == "openai":
            output_path = self._generate_openai(config)
        elif config.provider == "elevenlabs":
            output_path = self._generate_elevenlabs(config)
        else:
            raise ValueError(f"Provider no soportado: {config.provider}")

        return EngineResult(
            scene_id="audio",
            output_path=output_path,
            duration=0.0,  # TODO: Calcular duración real
        )

    def validate(self, config: AudioConfig) -> bool:
        """Valida la configuración de audio."""
        return config.provider in ("openai", "elevenlabs")

    def _generate_openai(self, config: AudioConfig) -> Path:
        """Genera audio usando OpenAI TTS."""
        from openai import OpenAI

        client = OpenAI()
        output_path = self._temp_dir / f"{hash(config.text)}.mp3"

        response = client.audio.speech.create(
            model="tts-1",
            voice=config.voice,
            input=config.text,
            speed=config.speed,
        )

        response.stream_to_file(output_path)
        return output_path

    def _generate_elevenlabs(self, config: AudioConfig) -> Path:
        """Genera audio usando ElevenLabs TTS."""
        # TODO: Implementar integración con ElevenLabs
        raise NotImplementedError("ElevenLabs TTS pendiente de implementación")
