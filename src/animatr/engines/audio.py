"""Engine de audio/TTS para ANIMATR."""

import hashlib
import os
import tempfile
from pathlib import Path

import requests
from mutagen.mp3 import MP3

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

        duration = self._get_audio_duration(output_path)

        return EngineResult(
            scene_id="audio",
            output_path=output_path,
            duration=duration,
        )

    def validate(self, config: AudioConfig) -> bool:
        """Valida la configuración de audio."""
        return config.provider in ("openai", "elevenlabs")

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Obtiene la duración real del archivo de audio en segundos."""
        audio = MP3(audio_path)
        return audio.info.length

    def _generate_openai(self, config: AudioConfig) -> Path:
        """Genera audio usando OpenAI TTS."""
        from openai import OpenAI

        client = OpenAI()
        output_path = self._temp_dir / f"{hashlib.md5(config.text.encode()).hexdigest()[:16]}.mp3"

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
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY no está configurada")

        voice_id = config.voice
        output_path = self._temp_dir / f"{hashlib.md5(config.text.encode()).hexdigest()[:16]}.mp3"

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        }
        data = {
            "text": config.text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
            },
        }

        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path
