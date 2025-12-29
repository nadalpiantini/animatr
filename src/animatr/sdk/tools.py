"""MCP Tools para ANIMATR.

Define las herramientas que Claude Agent SDK puede usar
para interactuar con el sistema de agentes y el pipeline de render.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from animatr.agents.crew import AnimatrCrew
from animatr.agents.input_detector import DetectionResult, InputDetector, InputType
from animatr.orchestrator import Orchestrator
from animatr.schema import AnimationSpec


class RunCrewInput(BaseModel):
    """Input para ejecutar el crew de agentes."""

    user_input: str = Field(..., description="Input del usuario (prompt, brief, script, o yaml)")
    max_iterations: int = Field(default=3, description="Máximo de iteraciones del feedback loop")
    verbose: bool = Field(default=True, description="Mostrar output detallado")


class RunCrewOutput(BaseModel):
    """Output de la ejecución del crew."""

    success: bool
    result: str
    approved: bool
    iterations: int
    input_type: str


class RenderInput(BaseModel):
    """Input para renderizar un spec."""

    spec_path: str = Field(..., description="Path al archivo YAML del spec")
    output_path: str = Field(..., description="Path para el video de salida")


class RenderOutput(BaseModel):
    """Output del render."""

    success: bool
    video_path: str | None = None
    error: str | None = None
    duration: float | None = None


class ValidateSpecInput(BaseModel):
    """Input para validar un spec."""

    spec_content: str = Field(..., description="Contenido YAML del spec")


class ValidateSpecOutput(BaseModel):
    """Output de la validación."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PreviewInput(BaseModel):
    """Input para preview rápido."""

    spec_path: str = Field(..., description="Path al spec")
    duration: int = Field(default=5, description="Duración del preview en segundos")


class AnimatrTools:
    """Herramientas MCP para ANIMATR."""

    def __init__(self) -> None:
        self.detector = InputDetector()
        self._crew: AnimatrCrew | None = None

    @property
    def crew(self) -> AnimatrCrew:
        """Lazy initialization del crew."""
        if self._crew is None:
            self._crew = AnimatrCrew()
        return self._crew

    def run_crew(self, input_data: RunCrewInput) -> RunCrewOutput:
        """Ejecuta el crew de agentes para crear un video.

        Esta es la herramienta principal que coordina todo el proceso
        de creación de video desde cualquier tipo de input.
        """
        try:
            # Detectar tipo de input
            detection = self.detector.detect(input_data.user_input)

            # Si es YAML spec, bypass a render directo
            if detection.input_type == InputType.YAML_SPEC:
                return RunCrewOutput(
                    success=True,
                    result="YAML spec detected - ready for direct render",
                    approved=True,
                    iterations=0,
                    input_type=detection.input_type.value,
                )

            # Ejecutar crew con feedback loop
            result, approved = self.crew.run_with_feedback_loop(
                detection,
                max_iterations=input_data.max_iterations,
            )

            return RunCrewOutput(
                success=True,
                result=result,
                approved=approved,
                iterations=self.crew._crew.iteration if hasattr(self.crew, '_crew') else 1,
                input_type=detection.input_type.value,
            )

        except Exception as e:
            return RunCrewOutput(
                success=False,
                result=f"Error: {e!s}",
                approved=False,
                iterations=0,
                input_type="error",
            )

    def render(self, input_data: RenderInput) -> RenderOutput:
        """Renderiza un spec YAML a video.

        Usa el pipeline existente de ANIMATR con FFmpeg.
        """
        try:
            spec_path = Path(input_data.spec_path)
            output_path = Path(input_data.output_path)

            # Cargar spec
            spec = AnimationSpec.from_yaml(spec_path)

            # Crear orchestrator y renderizar
            orchestrator = Orchestrator(spec)
            result_path = orchestrator.render(output_path)

            # Calcular duración total
            total_duration = sum(scene.duration_seconds for scene in spec.scenes)

            return RenderOutput(
                success=True,
                video_path=str(result_path),
                duration=total_duration,
            )

        except Exception as e:
            return RenderOutput(
                success=False,
                error=str(e),
            )

    def validate_spec(self, input_data: ValidateSpecInput) -> ValidateSpecOutput:
        """Valida un spec YAML contra el schema."""
        import yaml
        from pydantic import ValidationError

        errors: list[str] = []
        warnings: list[str] = []

        try:
            # Parsear YAML
            data = yaml.safe_load(input_data.spec_content)

            if not data:
                errors.append("Empty YAML content")
                return ValidateSpecOutput(valid=False, errors=errors)

            # Validar contra schema
            spec = AnimationSpec.model_validate(data)

            # Validaciones adicionales
            if not spec.scenes:
                errors.append("No scenes defined")

            for scene in spec.scenes:
                if scene.duration_seconds <= 0:
                    errors.append(f"Scene {scene.id}: duration must be positive")

                if scene.audio and not scene.audio.text:
                    warnings.append(f"Scene {scene.id}: audio defined but no text")

            return ValidateSpecOutput(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
            )

        except yaml.YAMLError as e:
            errors.append(f"YAML parse error: {e}")
            return ValidateSpecOutput(valid=False, errors=errors)

        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                errors.append(f"{loc}: {err['msg']}")
            return ValidateSpecOutput(valid=False, errors=errors)

    def preview(self, input_data: PreviewInput) -> dict[str, Any]:
        """Genera un preview rápido del spec.

        Solo procesa los primeros N segundos para validación rápida.
        """
        try:
            spec_path = Path(input_data.spec_path)
            spec = AnimationSpec.from_yaml(spec_path)

            # Información del preview
            preview_info = {
                "total_scenes": len(spec.scenes),
                "total_duration": sum(s.duration_seconds for s in spec.scenes),
                "preview_duration": min(input_data.duration, sum(s.duration_seconds for s in spec.scenes)),
                "output_config": {
                    "format": spec.output.format,
                    "resolution": spec.output.resolution,
                    "fps": spec.output.fps,
                },
                "scenes_preview": [],
            }

            cumulative = 0.0
            for scene in spec.scenes:
                if cumulative >= input_data.duration:
                    break

                preview_info["scenes_preview"].append({
                    "id": scene.id,
                    "duration": scene.duration,
                    "has_audio": scene.audio is not None,
                    "has_character": scene.character is not None,
                    "background_type": (
                        "color" if scene.background and scene.background.color
                        else "image" if scene.background and scene.background.image
                        else "video" if scene.background and scene.background.video
                        else "none"
                    ),
                })

                cumulative += scene.duration_seconds

            return {"success": True, **preview_info}

        except Exception as e:
            return {"success": False, "error": str(e)}


# Definición de herramientas para MCP
ANIMATR_TOOLS = [
    {
        "name": "run_crew",
        "description": "Execute the AI crew to create a video from any input type",
        "input_schema": RunCrewInput.model_json_schema(),
    },
    {
        "name": "render",
        "description": "Render an AnimationSpec YAML to video",
        "input_schema": RenderInput.model_json_schema(),
    },
    {
        "name": "validate_spec",
        "description": "Validate an AnimationSpec YAML against the schema",
        "input_schema": ValidateSpecInput.model_json_schema(),
    },
    {
        "name": "preview",
        "description": "Generate a quick preview of a spec",
        "input_schema": PreviewInput.model_json_schema(),
    },
]
