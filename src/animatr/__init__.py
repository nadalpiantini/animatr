"""ANIMATR - Motor Declarativo de Animación Audiovisual.

Un motor declarativo que permite crear videos animados profesionales
describiendo escenas en YAML, con soporte para agentes AI que pueden
crear videos desde prompts, briefs, scripts o specs completos.
"""

__version__ = "0.1.0"

from animatr.schema import AnimationSpec, AudioConfig, Character, Scene

__all__ = [
    "__version__",
    "AnimationSpec",
    "AudioConfig",
    "Character",
    "Scene",
]
