"""ANIMATR AI Agents Module.

Este módulo contiene el sistema de agentes AI que pueden crear videos
desde diferentes tipos de input: prompts, briefs, scripts, o YAML specs.
"""

from animatr.agents.crew import AnimatrCrew
from animatr.agents.input_detector import InputDetector, InputType

__all__ = ["AnimatrCrew", "InputDetector", "InputType"]
