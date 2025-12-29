"""Permission Hooks para ANIMATR Agent SDK.

Define hooks de permisos y validación que se ejecutan
antes y después de operaciones críticas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from animatr.schema import AnimationSpec


class HookType(Enum):
    """Tipos de hooks disponibles."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    PRE_RENDER = "PreRender"
    POST_RENDER = "PostRender"
    PRE_CREW = "PreCrew"
    POST_CREW = "PostCrew"


@dataclass
class HookContext:
    """Contexto pasado a los hooks."""

    tool_name: str
    input_data: Any
    output_data: Any | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class HookDecision:
    """Decisión de un hook."""

    allow: bool = True
    reason: str = ""
    modified_data: Any = None


class HookRegistry:
    """Registro centralizado de hooks."""

    def __init__(self) -> None:
        self._hooks: dict[HookType, list[Callable[[HookContext], HookDecision]]] = {
            hook_type: [] for hook_type in HookType
        }

    def register(
        self,
        hook_type: HookType,
        hook: Callable[[HookContext], HookDecision],
    ) -> None:
        """Registra un hook."""
        self._hooks[hook_type].append(hook)

    def execute(
        self,
        hook_type: HookType,
        context: HookContext,
    ) -> HookDecision:
        """Ejecuta todos los hooks de un tipo."""
        for hook in self._hooks[hook_type]:
            decision = hook(context)
            if not decision.allow:
                return decision
        return HookDecision(allow=True)


# Hooks predefinidos

def validate_spec_hook(context: HookContext) -> HookDecision:
    """Valida que el spec sea válido antes de render."""
    if context.tool_name not in ("render", "run_crew"):
        return HookDecision(allow=True)

    spec = context.input_data
    if hasattr(spec, "scenes") and not spec.scenes:
        return HookDecision(
            allow=False,
            reason="Spec must have at least one scene",
        )

    return HookDecision(allow=True)


def check_audio_config_hook(context: HookContext) -> HookDecision:
    """Verifica configuración de audio antes de render."""
    if context.tool_name != "render":
        return HookDecision(allow=True)

    spec = context.input_data
    if not hasattr(spec, "scenes"):
        return HookDecision(allow=True)

    import os
    for scene in spec.scenes:
        if scene.audio:
            if scene.audio.provider == "elevenlabs":
                if not os.environ.get("ELEVENLABS_API_KEY"):
                    return HookDecision(
                        allow=False,
                        reason=f"Scene {scene.id} uses ElevenLabs but ELEVENLABS_API_KEY not set",
                    )
            elif scene.audio.provider == "openai":
                if not os.environ.get("OPENAI_API_KEY"):
                    return HookDecision(
                        allow=False,
                        reason=f"Scene {scene.id} uses OpenAI but OPENAI_API_KEY not set",
                    )

    return HookDecision(allow=True)


def log_operation_hook(context: HookContext) -> HookDecision:
    """Hook de logging para debugging."""
    print(f"🔧 Tool: {context.tool_name}")
    if context.output_data:
        print(f"   Output: {type(context.output_data).__name__}")
    return HookDecision(allow=True)


def cost_estimation_hook(context: HookContext) -> HookDecision:
    """Estima y reporta costos de operaciones."""
    if context.tool_name not in ("run_crew", "render"):
        return HookDecision(allow=True)

    # Estimaciones aproximadas
    estimated_costs = {
        "run_crew": 0.50,  # USD por ejecución promedio
        "render": 0.10,  # USD por minuto de video
    }

    estimated = estimated_costs.get(context.tool_name, 0)
    print(f"💰 Estimated cost: ${estimated:.2f}")

    return HookDecision(allow=True)


def rate_limit_hook(context: HookContext) -> HookDecision:
    """Hook de rate limiting (placeholder)."""
    # En producción, implementar rate limiting real
    return HookDecision(allow=True)


# Factory para crear registry con hooks por defecto
def create_default_registry() -> HookRegistry:
    """Crea un registry con hooks por defecto."""
    registry = HookRegistry()

    # Hooks pre-tool
    registry.register(HookType.PRE_TOOL_USE, validate_spec_hook)
    registry.register(HookType.PRE_TOOL_USE, check_audio_config_hook)
    registry.register(HookType.PRE_TOOL_USE, cost_estimation_hook)

    # Hooks post-tool
    registry.register(HookType.POST_TOOL_USE, log_operation_hook)

    return registry
