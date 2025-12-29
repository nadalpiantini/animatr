"""Orchestrator que coordina los engines de ANIMATR."""

import subprocess
import tempfile
from pathlib import Path

from animatr.engines.audio import AudioEngine
from animatr.engines.base import EngineResult
from animatr.schema import AnimationSpec, Scene


class Orchestrator:
    """Coordina la ejecución de engines para renderizar un video."""

    def __init__(self, spec: AnimationSpec) -> None:
        self.spec = spec
        self.audio_engine = AudioEngine()
        self._temp_dir = Path(tempfile.mkdtemp(prefix="animatr_video_"))

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
        duration = scene.duration_seconds

        if scene.audio:
            audio_result = self.audio_engine.process(scene.audio)
            audio_path = audio_result.output_path
            duration = audio_result.duration

        return EngineResult(
            scene_id=scene.id,
            output_path=audio_path,
            duration=duration,
            metadata={"background": scene.background},
        )

    def _compose_video(
        self, scene_results: list[EngineResult], output_path: Path
    ) -> Path:
        """Compone el video final desde los resultados de escenas usando FFmpeg."""
        output_config = self.spec.output
        width = output_config.width
        height = output_config.height
        fps = output_config.fps

        if not scene_results:
            raise ValueError("No hay escenas para componer")

        concat_file = self._temp_dir / "concat.txt"
        segment_paths: list[Path] = []

        for i, result in enumerate(scene_results):
            segment_path = self._temp_dir / f"segment_{i}.mp4"
            self._create_segment(result, segment_path, width, height, fps)
            segment_paths.append(segment_path)

        with open(concat_file, "w") as f:
            for segment_path in segment_paths:
                f.write(f"file '{segment_path}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-r", str(fps),
            str(output_path),
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def _create_segment(
        self,
        result: EngineResult,
        output_path: Path,
        width: int,
        height: int,
        fps: int,
    ) -> None:
        """Crea un segmento de video para una escena."""
        duration = result.duration
        background_color = "0x1a1a2e"

        if result.metadata and result.metadata.get("background"):
            bg = result.metadata["background"]
            if bg.color:
                background_color = bg.color.replace("#", "0x")

        if result.output_path:
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", f"color=c={background_color}:s={width}x{height}:r={fps}:d={duration}",
                "-i", str(result.output_path),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                str(output_path),
            ]
        else:
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", f"color=c={background_color}:s={width}x{height}:r={fps}:d={duration}",
                "-c:v", "libx264",
                "-an",
                str(output_path),
            ]

        subprocess.run(cmd, check=True, capture_output=True)
