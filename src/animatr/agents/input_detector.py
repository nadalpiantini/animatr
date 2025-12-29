"""Detector de tipo de input para ANIMATR.

Clasifica el input del usuario en 4 categorías:
- YAML_SPEC: Spec completo → bypass agents, render directo
- BRIEF: Brief estructurado → partial crew (skip Intake)
- SCRIPT: Guion con escenas → full crew
- PROMPT: Lenguaje natural → full crew + discovery
"""

import json
import re
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from animatr.schema import AnimationSpec


class InputType(Enum):
    """Tipos de input soportados."""

    YAML_SPEC = "yaml_spec"  # Bypass agents → direct render
    BRIEF = "brief"  # Partial crew (skip Intake)
    SCRIPT = "script"  # Full crew
    PROMPT = "prompt"  # Full crew + discovery


class CreativeBrief(BaseModel):
    """Brief estructurado para creación de video."""

    topic: str
    duration: int | None = None  # segundos
    tone: str | None = None
    audience: str | None = None
    style: str | None = None
    key_points: list[str] | None = None


class DetectionResult(BaseModel):
    """Resultado de la detección de input."""

    input_type: InputType
    content: str
    parsed_spec: AnimationSpec | None = None
    parsed_brief: CreativeBrief | None = None
    confidence: float = 1.0

    class Config:
        arbitrary_types_allowed = True


class InputDetector:
    """Detecta el tipo de input y lo parsea apropiadamente."""

    # Patrones para detectar scripts
    SCRIPT_PATTERNS = [
        r"ESCENA\s*\d+",
        r"SCENE\s*\d+",
        r"\[.*?\].*?:",  # [action] CHARACTER:
        r"^[A-Z]+:",  # CHARACTER: dialogue
        r"INT\.|EXT\.",  # Screenplay format
        r"FADE IN|FADE OUT",
    ]

    # Keywords que sugieren brief estructurado
    BRIEF_KEYWORDS = [
        "topic",
        "duration",
        "tone",
        "audience",
        "style",
        "tema",
        "duración",
        "tono",
        "audiencia",
        "estilo",
    ]

    def detect(self, input_data: str | Path) -> DetectionResult:
        """Detecta el tipo de input y retorna resultado estructurado."""
        # Si es un path, leer el archivo
        if isinstance(input_data, Path):
            content = input_data.read_text()
            # Detectar por extensión primero
            if input_data.suffix in (".yaml", ".yml"):
                return self._try_yaml_spec(content)
            elif input_data.suffix == ".json":
                return self._try_json_brief(content)
        else:
            content = input_data.strip()

        # Intentar detectar YAML spec primero
        if self._looks_like_yaml(content):
            result = self._try_yaml_spec(content)
            if result.input_type == InputType.YAML_SPEC:
                return result

        # Intentar detectar JSON brief
        if self._looks_like_json(content):
            result = self._try_json_brief(content)
            if result.input_type == InputType.BRIEF:
                return result

        # Detectar si es un script
        if self._is_script(content):
            return DetectionResult(
                input_type=InputType.SCRIPT,
                content=content,
                confidence=0.85,
            )

        # Detectar si parece un brief en texto
        if self._is_text_brief(content):
            brief = self._parse_text_brief(content)
            return DetectionResult(
                input_type=InputType.BRIEF,
                content=content,
                parsed_brief=brief,
                confidence=0.7,
            )

        # Default: prompt natural
        return DetectionResult(
            input_type=InputType.PROMPT,
            content=content,
            confidence=0.9,
        )

    def _looks_like_yaml(self, content: str) -> bool:
        """Verifica si el contenido parece YAML."""
        yaml_indicators = ["version:", "scenes:", "output:", "---"]
        return any(indicator in content for indicator in yaml_indicators)

    def _looks_like_json(self, content: str) -> bool:
        """Verifica si el contenido parece JSON."""
        stripped = content.strip()
        return stripped.startswith("{") and stripped.endswith("}")

    def _try_yaml_spec(self, content: str) -> DetectionResult:
        """Intenta parsear como AnimationSpec YAML."""
        try:
            data = yaml.safe_load(content)
            if data and isinstance(data, dict):
                spec = AnimationSpec.model_validate(data)
                return DetectionResult(
                    input_type=InputType.YAML_SPEC,
                    content=content,
                    parsed_spec=spec,
                    confidence=1.0,
                )
        except (yaml.YAMLError, ValidationError):
            pass

        return DetectionResult(
            input_type=InputType.PROMPT,
            content=content,
            confidence=0.5,
        )

    def _try_json_brief(self, content: str) -> DetectionResult:
        """Intenta parsear como brief JSON."""
        try:
            data = json.loads(content)
            if data and isinstance(data, dict):
                # Verificar si tiene campos de brief
                if any(key in data for key in self.BRIEF_KEYWORDS):
                    brief = CreativeBrief.model_validate(data)
                    return DetectionResult(
                        input_type=InputType.BRIEF,
                        content=content,
                        parsed_brief=brief,
                        confidence=0.95,
                    )
        except (json.JSONDecodeError, ValidationError):
            pass

        return DetectionResult(
            input_type=InputType.PROMPT,
            content=content,
            confidence=0.5,
        )

    def _is_script(self, content: str) -> bool:
        """Verifica si el contenido parece un guion/script."""
        matches = sum(
            1 for pattern in self.SCRIPT_PATTERNS if re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        )
        return matches >= 2

    def _is_text_brief(self, content: str) -> bool:
        """Verifica si parece un brief en formato texto."""
        # Buscar patrones como "Topic: X" o "Tema: Y"
        brief_pattern = r"^(topic|tema|duration|duración|tone|tono|audience|audiencia):\s*\w+"
        return bool(re.search(brief_pattern, content, re.MULTILINE | re.IGNORECASE))

    def _parse_text_brief(self, content: str) -> CreativeBrief:
        """Parsea un brief desde texto estructurado."""
        lines = content.strip().split("\n")
        data: dict[str, str | int | list[str]] = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                # Mapear a campos del brief
                if key in ("topic", "tema"):
                    data["topic"] = value
                elif key in ("duration", "duración"):
                    # Extraer número
                    match = re.search(r"\d+", value)
                    if match:
                        data["duration"] = int(match.group())
                elif key in ("tone", "tono"):
                    data["tone"] = value
                elif key in ("audience", "audiencia"):
                    data["audience"] = value
                elif key in ("style", "estilo"):
                    data["style"] = value

        # Asegurar que topic existe
        if "topic" not in data:
            data["topic"] = content[:100]  # Usar primeros 100 chars

        return CreativeBrief.model_validate(data)
