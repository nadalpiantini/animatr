"""Modelos Pydantic para specs de ANIMATR."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class OutputConfig(BaseModel):
    """Configuración de salida del video."""

    format: Literal["mp4", "mov", "webm"] = "mp4"
    resolution: str = "1920x1080"
    fps: int = Field(default=30, ge=1, le=120)

    @property
    def width(self) -> int:
        return int(self.resolution.split("x")[0])

    @property
    def height(self) -> int:
        return int(self.resolution.split("x")[1])


class AudioConfig(BaseModel):
    """Configuración de audio/TTS para una escena."""

    text: str = Field(..., min_length=1)
    voice: str = "alloy"
    provider: Literal["openai", "elevenlabs"] = "openai"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class Character(BaseModel):
    """Configuración de personaje animado."""

    asset: str = Field(..., description="Path al archivo del personaje (.moho)")
    position: Literal["left", "center", "right"] = "center"
    expression: str = "neutral"
    scale: float = Field(default=1.0, ge=0.1, le=3.0)


class Background(BaseModel):
    """Configuración de fondo de escena."""

    color: str | None = None
    image: str | None = None
    video: str | None = None


class Scene(BaseModel):
    """Una escena individual del video."""

    id: str = Field(..., min_length=1)
    duration: str = Field(..., pattern=r"^\d+(\.\d+)?s$")
    character: Character | None = None
    audio: AudioConfig | None = None
    background: Background | None = None

    @property
    def duration_seconds(self) -> float:
        return float(self.duration.rstrip("s"))


class AnimationSpec(BaseModel):
    """Spec completo de animación ANIMATR."""

    version: str = "1.0"
    output: OutputConfig = Field(default_factory=OutputConfig)
    scenes: list[Scene] = Field(default_factory=list, min_length=1)

    @classmethod
    def from_yaml(cls, path: Path) -> "AnimationSpec":
        """Carga un spec desde un archivo YAML."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def to_yaml(self, path: Path) -> None:
        """Guarda el spec a un archivo YAML."""
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)
