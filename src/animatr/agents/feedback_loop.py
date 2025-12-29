"""FeedbackLoopController - Control del ciclo de revisión y mejora.

Coordina el proceso iterativo de render → QA → revisión
hasta que el video sea aprobado o se agoten los intentos.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from animatr.agents.crew import AnimatrCrew
    from animatr.agents.input_detector import DetectionResult


class RevisionType(Enum):
    """Tipo de revisión requerida."""

    NARRATIVE = "narrative"  # → Head Filmmaker
    VISUAL = "visual"  # → Head Animator
    TECHNICAL = "technical"  # → Técnico
    AUDIO = "audio"  # → Guionista (reescribir) o Renderer (regenerar)


@dataclass
class QAFeedback:
    """Feedback estructurado del QA agent."""

    scores: dict[str, float] = field(default_factory=dict)
    is_approved: bool = False
    issues: list[dict[str, str]] = field(default_factory=list)
    overall_score: float = 0.0

    @classmethod
    def from_qa_output(cls, output: str) -> "QAFeedback":
        """Parsea el output del QA agent."""
        feedback = cls()

        # Intentar extraer JSON si está presente
        json_match = re.search(r"\{[\s\S]*\}", output)
        if json_match:
            try:
                data = json.loads(json_match.group())
                feedback.scores = data.get("scores", {})
                feedback.is_approved = data.get("approved", False)
                feedback.issues = data.get("issues", [])
                feedback.overall_score = data.get("overall_score", 0.0)
                return feedback
            except json.JSONDecodeError:
                pass

        # Fallback: parseo basado en texto
        if "APPROVED" in output.upper():
            feedback.is_approved = True
        elif "REVISION" in output.upper():
            feedback.is_approved = False

        # Extraer score si está presente
        score_match = re.search(r"(\d+(?:\.\d+)?)\s*%", output)
        if score_match:
            feedback.overall_score = float(score_match.group(1)) / 100

        return feedback


@dataclass
class RevisionRequest:
    """Solicitud de revisión para un agente específico."""

    revision_type: RevisionType
    issue: str
    suggested_fix: str
    priority: int = 1  # 1 = high, 2 = medium, 3 = low


class FeedbackLoopController:
    """Controla el ciclo de feedback entre render y QA."""

    def __init__(
        self,
        crew: "AnimatrCrew",
        max_iterations: int = 3,
    ) -> None:
        self.crew = crew
        self.max_iterations = max_iterations
        self.iteration = 0
        self.history: list[QAFeedback] = []

    def run(self, detection: "DetectionResult") -> tuple[str, bool]:
        """Ejecuta el loop de feedback.

        Returns:
            Tuple de (resultado final, fue aprobado)
        """
        result = ""

        while self.iteration < self.max_iterations:
            self.iteration += 1
            print(f"\n🔄 Iteration {self.iteration}/{self.max_iterations}")

            # Ejecutar crew
            result = self.crew.kickoff(detection)

            # Parsear feedback del QA
            feedback = QAFeedback.from_qa_output(result)
            self.history.append(feedback)

            print(f"📊 Score: {feedback.overall_score:.1%}")

            if feedback.is_approved:
                print("✅ Video approved!")
                return result, True

            # Si no está aprobado, identificar revisiones necesarias
            revisions = self._identify_revisions(feedback)

            if not revisions:
                print("⚠️ QA rejected but no specific revisions identified")
                continue

            # Aplicar revisiones para siguiente iteración
            self._apply_revisions(revisions)

        # Agotamos intentos
        print(f"\n🚨 Max iterations ({self.max_iterations}) reached")
        print("👤 Human review required")
        return result, False

    def _identify_revisions(self, feedback: QAFeedback) -> list[RevisionRequest]:
        """Identifica las revisiones necesarias desde el feedback."""
        revisions: list[RevisionRequest] = []

        for issue in feedback.issues:
            revision_type = self._classify_issue(issue.get("type", ""))
            revisions.append(
                RevisionRequest(
                    revision_type=revision_type,
                    issue=issue.get("description", "Unknown issue"),
                    suggested_fix=issue.get("fix", "Review and fix"),
                    priority=issue.get("priority", 2),
                )
            )

        # Ordenar por prioridad
        revisions.sort(key=lambda r: r.priority)
        return revisions

    def _classify_issue(self, issue_type: str) -> RevisionType:
        """Clasifica el tipo de issue para routing."""
        issue_lower = issue_type.lower()

        if any(kw in issue_lower for kw in ["script", "dialogue", "pacing", "story"]):
            return RevisionType.NARRATIVE
        elif any(kw in issue_lower for kw in ["visual", "color", "composition", "design"]):
            return RevisionType.VISUAL
        elif any(kw in issue_lower for kw in ["audio", "voice", "lip-sync", "sound"]):
            return RevisionType.AUDIO
        else:
            return RevisionType.TECHNICAL

    def _apply_revisions(self, revisions: list[RevisionRequest]) -> None:
        """Aplica las revisiones identificadas.

        En una implementación completa, esto modificaría el contexto
        del crew para la siguiente iteración.
        """
        print(f"\n📝 Applying {len(revisions)} revision(s):")

        for rev in revisions:
            agent_name = self._get_responsible_agent(rev.revision_type)
            print(f"  → {rev.revision_type.value}: {rev.issue}")
            print(f"    Assigned to: {agent_name}")
            print(f"    Fix: {rev.suggested_fix}")

    def _get_responsible_agent(self, revision_type: RevisionType) -> str:
        """Determina qué agente es responsable de cada tipo de revisión."""
        mapping = {
            RevisionType.NARRATIVE: "Head Filmmaker → Guionista",
            RevisionType.VISUAL: "Head Animator → Designer",
            RevisionType.AUDIO: "Guionista (text) / Renderer (audio)",
            RevisionType.TECHNICAL: "Técnico",
        }
        return mapping.get(revision_type, "Director")

    def get_summary(self) -> dict:
        """Retorna resumen del proceso de feedback."""
        return {
            "total_iterations": self.iteration,
            "max_iterations": self.max_iterations,
            "final_approved": self.history[-1].is_approved if self.history else False,
            "score_progression": [f.overall_score for f in self.history],
            "issues_by_iteration": [len(f.issues) for f in self.history],
        }
