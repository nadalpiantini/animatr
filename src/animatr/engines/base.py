"""Clase base para engines de ANIMATR."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EngineResult:
    """Resultado de procesamiento de un engine."""

    scene_id: str
    output_path: Path | None
    duration: float
    metadata: dict[str, Any] | None = None


class Engine(ABC):
    """Clase base abstracta para todos los engines."""

    @abstractmethod
    def process(self, config: Any) -> EngineResult:
        """Procesa una configuración y retorna el resultado."""
        ...

    @abstractmethod
    def validate(self, config: Any) -> bool:
        """Valida que la configuración sea correcta."""
        ...
