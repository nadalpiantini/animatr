"""QA Agent - Control de calidad.

El QA Agent revisa el output del render y evalúa
si cumple con los estándares de calidad.
"""

from crewai import Agent

from animatr.agents.base import agent_factory


def create_qa_agent() -> Agent:
    """Crea el agente QA."""
    return agent_factory.create_agent(
        role="Quality Assurance Specialist",
        goal=(
            "Ensure every video meets quality standards before delivery. "
            "Analyze lip-sync accuracy, dialogue coherence, visual composition, "
            "audio quality, and technical specs. Provide actionable feedback for revisions."
        ),
        backstory=(
            "QA lead con experiencia en producción audiovisual y testing de software. "
            "Has desarrollado frameworks de calidad para estudios de animación "
            "y plataformas de video. Tu ojo crítico detecta problemas "
            "que otros pasan por alto: timing de lip-sync off por 50ms, "
            "inconsistencias de color, audio con ruido imperceptible. "
            "Reportas al Head Filmmaker."
        ),
        verbose=True,
        allow_delegation=False,
    )


class QAScoring:
    """Sistema de puntuación de calidad."""

    WEIGHTS = {
        "lip_sync": 0.25,  # ±50ms tolerance
        "dialogue": 0.20,  # Coherence
        "pacing": 0.15,  # Matches spec
        "visual": 0.20,  # Composition
        "audio": 0.15,  # Clear, no noise
        "technical": 0.05,  # Specs met
    }

    THRESHOLD = 0.80  # 80% para aprobar

    @classmethod
    def calculate_score(cls, scores: dict[str, float]) -> float:
        """Calcula score total ponderado."""
        total = 0.0
        for aspect, weight in cls.WEIGHTS.items():
            if aspect in scores:
                total += scores[aspect] * weight
        return total

    @classmethod
    def is_approved(cls, scores: dict[str, float], has_critical: bool = False) -> bool:
        """Determina si el video está aprobado."""
        if has_critical:
            return False
        return cls.calculate_score(scores) >= cls.THRESHOLD
