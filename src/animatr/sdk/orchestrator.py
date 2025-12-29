"""Claude Agent SDK Orchestrator para ANIMATR.

Este módulo proporciona la integración con Claude Agent SDK
para orquestar el sistema de agentes desde un nivel superior.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from animatr.agents.crew import AnimatrCrew
from animatr.agents.input_detector import DetectionResult, InputDetector, InputType
from animatr.orchestrator import Orchestrator
from animatr.schema import AnimationSpec
from animatr.sdk.tools import AnimatrTools


@dataclass
class AgentConfig:
    """Configuración para el Agent SDK orchestrator."""

    max_turns: int = 20
    max_budget_usd: float = 2.0
    allowed_tools: list[str] = field(default_factory=lambda: ["mcp__animatr__*"])
    verbose: bool = True


@dataclass
class HookResult:
    """Resultado de un hook."""

    allow: bool = True
    message: str = ""
    modified_input: Any = None


class AgentOrchestrator:
    """Orchestrador de alto nivel usando Claude Agent SDK concepts.

    Este orchestrador coordina:
    - Detección de tipo de input
    - Routing a crew de agentes o render directo
    - Hooks de validación pre/post ejecución
    - Control de permisos y presupuesto
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig()
        self.tools = AnimatrTools()
        self.detector = InputDetector()

        # Hooks
        self._pre_tool_hooks: list[Callable] = []
        self._post_tool_hooks: list[Callable] = []

        # Estado
        self._turns_used = 0
        self._budget_used = 0.0

    def register_pre_hook(self, hook: Callable[[str, Any], HookResult]) -> None:
        """Registra un hook pre-ejecución de herramienta."""
        self._pre_tool_hooks.append(hook)

    def register_post_hook(self, hook: Callable[[str, Any, Any], HookResult]) -> None:
        """Registra un hook post-ejecución de herramienta."""
        self._post_tool_hooks.append(hook)

    def _run_pre_hooks(self, tool_name: str, input_data: Any) -> HookResult:
        """Ejecuta hooks pre-tool."""
        for hook in self._pre_tool_hooks:
            result = hook(tool_name, input_data)
            if not result.allow:
                return result
        return HookResult(allow=True)

    def _run_post_hooks(self, tool_name: str, input_data: Any, output: Any) -> HookResult:
        """Ejecuta hooks post-tool."""
        for hook in self._post_tool_hooks:
            result = hook(tool_name, input_data, output)
            if not result.allow:
                return result
        return HookResult(allow=True)

    def process_input(
        self,
        user_input: str | Path,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Procesa input del usuario y genera video.

        Este es el punto de entrada principal que:
        1. Detecta el tipo de input
        2. Ejecuta el flujo apropiado (crew o render directo)
        3. Retorna el resultado

        Args:
            user_input: Prompt, brief, script, o path a YAML
            output_path: Path para el video de salida

        Returns:
            Dict con resultado de la operación
        """
        # Detectar tipo de input
        detection = self.detector.detect(user_input)

        if self.config.verbose:
            print(f"📥 Input type detected: {detection.input_type.value}")
            print(f"   Confidence: {detection.confidence:.0%}")

        # Routing basado en tipo
        if detection.input_type == InputType.YAML_SPEC:
            return self._handle_yaml_spec(detection, output_path)
        else:
            return self._handle_creative_input(detection, output_path)

    def _handle_yaml_spec(
        self,
        detection: DetectionResult,
        output_path: Path | None,
    ) -> dict[str, Any]:
        """Maneja YAML spec con bypass de agentes → render directo."""
        if self.config.verbose:
            print("⚡ YAML spec detected - bypassing agents")

        if not detection.parsed_spec:
            return {
                "success": False,
                "error": "Failed to parse YAML spec",
                "input_type": "yaml_spec",
            }

        if output_path is None:
            output_path = Path("output/video.mp4")

        # Pre-hook para render
        pre_result = self._run_pre_hooks("render", detection.parsed_spec)
        if not pre_result.allow:
            return {
                "success": False,
                "error": f"Pre-hook blocked: {pre_result.message}",
                "input_type": "yaml_spec",
            }

        try:
            # Render directo
            orchestrator = Orchestrator(detection.parsed_spec)
            video_path = orchestrator.render(output_path)

            result = {
                "success": True,
                "video_path": str(video_path),
                "input_type": "yaml_spec",
                "bypassed_agents": True,
            }

            # Post-hook
            self._run_post_hooks("render", detection.parsed_spec, result)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "input_type": "yaml_spec",
            }

    def _handle_creative_input(
        self,
        detection: DetectionResult,
        output_path: Path | None,
    ) -> dict[str, Any]:
        """Maneja input creativo con crew de agentes."""
        if self.config.verbose:
            print(f"🎬 Processing with AI crew ({detection.input_type.value})")

        # Pre-hook
        pre_result = self._run_pre_hooks("run_crew", detection)
        if not pre_result.allow:
            return {
                "success": False,
                "error": f"Pre-hook blocked: {pre_result.message}",
                "input_type": detection.input_type.value,
            }

        try:
            # Crear crew y ejecutar
            crew = AnimatrCrew(verbose=self.config.verbose)
            result, approved = crew.run_with_feedback_loop(
                detection,
                max_iterations=3,
            )

            response = {
                "success": True,
                "result": result,
                "approved": approved,
                "input_type": detection.input_type.value,
                "used_agents": True,
            }

            # Post-hook
            self._run_post_hooks("run_crew", detection, response)

            return response

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "input_type": detection.input_type.value,
            }

    def create(
        self,
        prompt: str,
        output: str = "output/video.mp4",
        no_agents: bool = False,
        preview: bool = False,
    ) -> dict[str, Any]:
        """Método conveniente para crear videos desde CLI.

        Args:
            prompt: Input del usuario (cualquier formato)
            output: Path para el video de salida
            no_agents: Si True, fuerza bypass de agentes
            preview: Si True, solo genera preview

        Returns:
            Dict con resultado
        """
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if preview:
            return self.tools.preview({"spec_path": prompt, "duration": 5})

        if no_agents:
            # Forzar bypass
            detection = self.detector.detect(prompt)
            if detection.input_type == InputType.YAML_SPEC:
                return self._handle_yaml_spec(detection, output_path)
            else:
                return {
                    "success": False,
                    "error": "--no-agents requires a valid YAML spec",
                }

        return self.process_input(prompt, output_path)


# Hooks predefinidos

def pre_render_validation(tool_name: str, input_data: Any) -> HookResult:
    """Hook que valida specs antes del render."""
    if tool_name != "render":
        return HookResult(allow=True)

    # Validar que el spec tiene escenas
    if hasattr(input_data, "scenes") and not input_data.scenes:
        return HookResult(
            allow=False,
            message="Spec has no scenes defined",
        )

    return HookResult(allow=True)


def post_render_qa(tool_name: str, input_data: Any, output: Any) -> HookResult:
    """Hook que ejecuta QA después del render."""
    if tool_name != "render":
        return HookResult(allow=True)

    # En una implementación completa, aquí se ejecutaría
    # análisis automático del video generado

    return HookResult(allow=True)


def budget_check(tool_name: str, input_data: Any) -> HookResult:
    """Hook que verifica presupuesto antes de operaciones costosas."""
    # Placeholder para control de costos
    return HookResult(allow=True)
