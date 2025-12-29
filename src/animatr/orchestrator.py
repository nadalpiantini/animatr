"""Orchestrator que coordina los engines de ANIMATR."""

from pathlib import Path

from animatr.engines.audio import AudioEngine
from animatr.engines.base import EngineResult
from animatr.schema import AnimationSpec, Scene


class Orchestrator:
    """Coordina la ejecución de engines para renderizar un video."""

    def __init__(self, spec: AnimationSpec) -> None:
        self.spec = spec
        self.audio_engine = AudioEngine()

    def render(self, output_path: Path) -> Path:
        """Renderiza el spec completo a un video."""
        scene_results: list[EngineResult] = []

        for scene in self.spec.scenes:
            result = self._process_scene(scene)
            scene_results.append(result)

        final_path = self._compose_video(scene_results, output_path)
        return final_path

    def _process_scene(self, scene: Scene) -> EngineResult:
        """Procesa una escena individual."""
        audio_path: Path | None = None

        if scene.audio:
            audio_result = self.audio_engine.process(scene.audio)
            audio_path = audio_result.output_path

        return EngineResult(
            scene_id=scene.id,
            output_path=audio_path,
            duration=scene.duration_seconds,
        )

    def _compose_video(
        self, scene_results: list[EngineResult], output_path: Path
    ) -> Path:
        """Compone el video final desde los resultados de escenas."""
        # TODO: Implementar composición con Blender/FFmpeg
        return output_path
