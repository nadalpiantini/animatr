"""AnimatrCrew - Orquestación de agentes con CrewAI.

Este módulo define el crew principal que coordina todos los agentes
para crear videos desde diferentes tipos de input.
"""

from pathlib import Path

from crewai import Crew, Process, Task

from animatr.agents.animator import create_head_animator
from animatr.agents.designer import create_designer
from animatr.agents.director import create_director
from animatr.agents.filmmaker import create_head_filmmaker
from animatr.agents.guionista import create_guionista
from animatr.agents.input_detector import CreativeBrief, DetectionResult, InputType
from animatr.agents.intake import create_intake_agent
from animatr.agents.qa import create_qa_agent
from animatr.agents.renderer import create_renderer
from animatr.agents.tecnico import create_tecnico


class AnimatrCrew:
    """Crew principal de ANIMATR para creación de videos."""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self._init_agents()

    def _init_agents(self) -> None:
        """Inicializa todos los agentes del crew."""
        # Jefes
        self.director = create_director()
        self.head_filmmaker = create_head_filmmaker()
        self.head_animator = create_head_animator()

        # Equipo Filmmaker
        self.intake = create_intake_agent()
        self.guionista = create_guionista()
        self.qa = create_qa_agent()

        # Equipo Animator
        self.designer = create_designer()
        self.tecnico = create_tecnico()
        self.renderer = create_renderer()

    def create_tasks_for_input(
        self, detection: DetectionResult
    ) -> list[Task]:
        """Crea las tareas apropiadas según el tipo de input."""
        tasks: list[Task] = []

        if detection.input_type == InputType.YAML_SPEC:
            # Bypass: solo render y QA
            tasks.extend(self._create_render_tasks(detection.content))

        elif detection.input_type == InputType.BRIEF:
            # Partial: skip intake, empezar desde guion
            tasks.extend(self._create_script_tasks(detection.parsed_brief))
            tasks.extend(self._create_design_tasks())
            tasks.extend(self._create_spec_tasks())
            tasks.extend(self._create_render_tasks())

        else:
            # Full crew: SCRIPT o PROMPT
            tasks.extend(self._create_intake_tasks(detection.content))
            tasks.extend(self._create_script_tasks())
            tasks.extend(self._create_design_tasks())
            tasks.extend(self._create_spec_tasks())
            tasks.extend(self._create_render_tasks())

        return tasks

    def _create_intake_tasks(self, user_input: str) -> list[Task]:
        """Tareas de análisis de input."""
        return [
            Task(
                description=f"""
                Analyze the user input and convert it to a structured creative brief.

                User Input:
                {user_input}

                Extract:
                - Main topic and message
                - Desired duration (infer if not specified)
                - Tone and style
                - Target audience
                - Key points to cover

                Output a structured CreativeBrief in JSON format.
                """,
                expected_output="A structured CreativeBrief in JSON format with topic, duration, tone, audience, style, and key_points.",
                agent=self.intake,
            )
        ]

    def _create_script_tasks(
        self, brief: CreativeBrief | None = None
    ) -> list[Task]:
        """Tareas de escritura de guion."""
        brief_context = ""
        if brief:
            brief_context = f"""
            Creative Brief:
            - Topic: {brief.topic}
            - Duration: {brief.duration or 'to be determined'}s
            - Tone: {brief.tone or 'professional'}
            - Audience: {brief.audience or 'general'}
            - Style: {brief.style or 'modern'}
            - Key Points: {', '.join(brief.key_points or [])}
            """

        return [
            Task(
                description=f"""
                Write an engaging script with natural dialogue and narration.

                {brief_context if brief_context else 'Use the creative brief from the previous task.'}

                Create:
                - Scene breakdown with clear transitions
                - Dialogue for characters (natural, TTS-friendly)
                - Narration text with emotion markers
                - Timing cues for each section

                Format as a structured script with ESCENA markers.
                """,
                expected_output="Complete script with scenes, dialogue, narration, emotions, and timing markers.",
                agent=self.guionista,
            )
        ]

    def _create_design_tasks(self) -> list[Task]:
        """Tareas de diseño visual."""
        return [
            Task(
                description="""
                Create visual design specifications for the video.

                Based on the script, define:
                - Character selection and configuration
                - Background colors and images
                - Scene composition and layout
                - Color palette for consistency
                - Visual transitions between scenes

                Output design specifications in structured format.
                """,
                expected_output="Visual design specs with characters, backgrounds, colors, and composition details.",
                agent=self.designer,
            )
        ]

    def _create_spec_tasks(self) -> list[Task]:
        """Tareas de generación de spec YAML."""
        return [
            Task(
                description="""
                Generate a valid AnimationSpec YAML from the script and design specs.

                The YAML must include:
                - version: "1.0"
                - output: format, resolution, fps
                - scenes: array with id, duration, character, audio, background

                Each scene must have:
                - id: unique identifier
                - duration: in format "Xs" (e.g., "5s")
                - audio: text, voice, provider, speed
                - background: color or image
                - character (optional): asset, position, expression

                Validate the spec structure before outputting.
                """,
                expected_output="Complete, valid AnimationSpec YAML ready for rendering.",
                agent=self.tecnico,
                output_file="output/spec.yaml",
            )
        ]

    def _create_render_tasks(self, spec_content: str | None = None) -> list[Task]:
        """Tareas de render."""
        spec_context = ""
        if spec_content:
            spec_context = f"Use this spec directly:\n{spec_content}"

        return [
            Task(
                description=f"""
                Execute the render pipeline to generate the final video.

                {spec_context if spec_context else 'Use the spec from the previous task.'}

                Steps:
                1. Validate the spec structure
                2. Generate audio for each scene using configured TTS
                3. Compose video with backgrounds and audio
                4. Apply transitions and effects
                5. Export final video in requested format

                Report any errors with specific details for troubleshooting.
                """,
                expected_output="Rendered video file path and production report.",
                agent=self.renderer,
            ),
            Task(
                description="""
                Review the rendered video for quality assurance.

                Evaluate:
                - Lip-sync accuracy (±50ms tolerance)
                - Dialogue coherence and naturalness
                - Pacing matches spec timings
                - Visual composition and consistency
                - Audio clarity (no noise, proper levels)
                - Technical specs (resolution, fps, format)

                Score each aspect 0-100 and provide:
                - Overall score (weighted average)
                - APPROVED/REVISION_NEEDED decision
                - Specific issues with recommended fixes
                - Which agent should handle each issue
                """,
                expected_output="QA report with scores, decision, and actionable feedback.",
                agent=self.qa,
            ),
        ]

    def create_crew(self, tasks: list[Task]) -> Crew:
        """Crea el crew con proceso jerárquico."""
        return Crew(
            agents=[
                self.director,
                self.head_filmmaker,
                self.head_animator,
                self.intake,
                self.guionista,
                self.qa,
                self.designer,
                self.tecnico,
                self.renderer,
            ],
            tasks=tasks,
            process=Process.hierarchical,
            manager_agent=self.director,
            verbose=self.verbose,
        )

    def kickoff(self, detection: DetectionResult) -> str:
        """Ejecuta el crew completo para el input dado."""
        tasks = self.create_tasks_for_input(detection)
        crew = self.create_crew(tasks)
        result = crew.kickoff()
        return str(result)

    def run_with_feedback_loop(
        self,
        detection: DetectionResult,
        max_iterations: int = 3,
    ) -> tuple[str, bool]:
        """Ejecuta con loop de feedback hasta aprobar o agotar intentos."""
        from animatr.agents.feedback_loop import FeedbackLoopController

        controller = FeedbackLoopController(self, max_iterations)
        return controller.run(detection)
