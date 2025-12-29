"""Intake Agent - Analista de input del usuario.

El Intake Agent procesa cualquier tipo de input del usuario
y lo convierte en un brief estructurado para el resto del crew.
"""

from crewai import Agent

from animatr.agents.base import agent_factory


def create_intake_agent() -> Agent:
    """Crea el agente Intake."""
    return agent_factory.create_agent(
        role="Input Analyst & Brief Creator",
        goal=(
            "Transform any user input into a comprehensive creative brief. "
            "Extract key requirements, identify implicit needs, and structure information "
            "for downstream creative processing. Handle prompts, briefs, scripts, and specs."
        ),
        backstory=(
            "Especialista en UX research y análisis de requerimientos creativos. "
            "Has trabajado en agencias digitales líderes ayudando a traducir "
            "ideas vagas de clientes en briefs accionables. Tu capacidad "
            "para hacer las preguntas correctas y estructurar información "
            "es clave para el éxito de cada proyecto. "
            "Reportas al Head Filmmaker."
        ),
        verbose=True,
        allow_delegation=False,
    )
