"""Guionista Agent - Escritor de guiones y diálogos.

El Guionista crea los scripts, diálogos, narraciones
y define las emociones para cada escena.
"""

from crewai import Agent

from animatr.agents.base import agent_factory


def create_guionista() -> Agent:
    """Crea el agente Guionista."""
    return agent_factory.create_agent(
        role="Scriptwriter & Dialogue Specialist",
        goal=(
            "Write engaging scripts with natural dialogue and compelling narration. "
            "Define emotional beats, timing cues, and voice directions for each scene. "
            "Ensure scripts are optimized for TTS and character animation."
        ),
        backstory=(
            "Guionista con experiencia en TV, publicidad y contenido digital. "
            "Has escrito para personajes animados, voiceovers comerciales "
            "y videos educativos. Tu especialidad es crear diálogos naturales "
            "que funcionan perfectamente con text-to-speech y lip-sync. "
            "Conoces las limitaciones técnicas y escribes pensando en ellas. "
            "Reportas al Head Filmmaker."
        ),
        verbose=True,
        allow_delegation=False,
    )
