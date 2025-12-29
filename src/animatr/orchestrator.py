"""Orchestrator que coordina los engines de ANIMATR.

Este módulo orquesta el pipeline completo de renderizado:
1. Audio Engine → Genera narración TTS
2. Moho Engine → Anima personajes 2D con lip-sync
3. Blender Engine → Compone escenas finales
4. FFmpeg → Ensambla video final
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from animatr.db.manager import ProjectManager
from animatr.db.models import RenderStatus
from animatr.engines.audio import AudioEngine
from animatr.engines.base import EngineResult
from animatr.engines.blender import BlenderEngine, BlenderSceneConfig
from animatr.engines.moho import MohoConfig, MohoEngine
from animatr.schema import AnimationSpec, Scene

logger = logging.getLogger(__name__)


@dataclass
class RenderProgress:
    """Estado del progreso de render."""

    total_scenes: int = 0
    completed_scenes: int = 0
    current_scene: str = ""
    current_phase: str = ""
    progress: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Verifica si el render está completo."""
        return self.completed_scenes >= self.total_scenes

    def update(self, scene_id: str, phase: str) -> None:
        """Actualiza el progreso."""
        self.current_scene = scene_id
        self.current_phase = phase
        if self.total_scenes > 0:
            base_progress = self.completed_scenes / self.total_scenes
            phase_weights = {
                "audio": 0.1,
                "moho": 0.4,
                "blender": 0.4,
                "compose": 0.1,
            }
            phase_progress = phase_weights.get(phase, 0) / self.total_scenes
            self.progress = base_progress + phase_progress


class Orchestrator:
    """Coordina la ejecución de engines para renderizar un video completo.

    Pipeline:
        Scene → Audio Engine → Moho Engine → Blender Engine → FFmpeg

    El orchestrator gestiona:
    - Ejecución secuencial de engines por escena
    - Paso de resultados entre engines
    - Composición final del video
    - Tracking de progreso
    """

    def __init__(
        self,
        spec: AnimationSpec,
        project_manager: ProjectManager | None = None,
        render_job_id: int | None = None,
    ) -> None:
        """Inicializa el orchestrator.

        Args:
            spec: AnimationSpec con la definición del video
            project_manager: Gestor de proyectos para persistencia
            render_job_id: ID del job de render para tracking
        """
        self.spec = spec
        self.project_manager = project_manager
        self.render_job_id = render_job_id

        # Engines
        self.audio_engine = AudioEngine()
        self.moho_engine = MohoEngine()
        self.blender_engine = BlenderEngine()

        # Working directories
        self._temp_dir = Path(tempfile.mkdtemp(prefix="animatr_render_"))
        self._audio_dir = self._temp_dir / "audio"
        self._moho_dir = self._temp_dir / "moho"
        self._blender_dir = self._temp_dir / "blender"
        self._output_dir = self._temp_dir / "output"

        for d in [self._audio_dir, self._moho_dir, self._blender_dir, self._output_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Progress tracking
        self.progress = RenderProgress(total_scenes=len(spec.scenes))
        self._progress_callbacks: list[Callable[[RenderProgress], None]] = []

    def on_progress(self, callback: Callable[[RenderProgress], None]) -> None:
        """Registra un callback para actualizaciones de progreso."""
        self._progress_callbacks.append(callback)

    def _notify_progress(self) -> None:
        """Notifica a todos los callbacks registrados."""
        for callback in self._progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

        # Actualizar en base de datos si disponible
        if self.project_manager and self.render_job_id:
            self.project_manager.update_render_job(
                self.render_job_id,
                progress=self.progress.progress,
                current_scene=self.progress.current_scene,
                completed_scenes=self.progress.completed_scenes,
            )

    def render(self, output_path: Path) -> Path:
        """Renderiza el spec completo a un video.

        Args:
            output_path: Path donde guardar el video final

        Returns:
            Path al video generado

        Raises:
            ValueError: Si no hay escenas para renderizar
            subprocess.CalledProcessError: Si FFmpeg falla
        """
        if not self.spec.scenes:
            raise ValueError("No hay escenas para renderizar")

        logger.info(f"Starting render of {len(self.spec.scenes)} scenes")

        # Actualizar estado a processing
        if self.project_manager and self.render_job_id:
            self.project_manager.update_render_job(
                self.render_job_id,
                status=RenderStatus.PROCESSING,
                total_scenes=len(self.spec.scenes),
            )

        scene_results: list[dict[str, Any]] = []

        try:
            for scene in self.spec.scenes:
                self.progress.update(scene.id, "processing")
                self._notify_progress()

                result = self._process_scene(scene)
                scene_results.append(result)

                self.progress.completed_scenes += 1
                self._notify_progress()

            # Componer video final
            self.progress.current_phase = "compose"
            self._notify_progress()

            final_path = self._compose_video(scene_results, output_path)

            # Marcar como completado
            if self.project_manager and self.render_job_id:
                self.project_manager.update_render_job(
                    self.render_job_id,
                    status=RenderStatus.COMPLETED,
                    progress=1.0,
                    output_path=str(final_path),
                )

            logger.info(f"Render complete: {final_path}")
            return final_path

        except Exception as e:
            logger.error(f"Render failed: {e}")
            self.progress.errors.append(str(e))

            if self.project_manager and self.render_job_id:
                self.project_manager.update_render_job(
                    self.render_job_id,
                    status=RenderStatus.FAILED,
                    error_message=str(e),
                )

            raise

    def _process_scene(self, scene: Scene) -> dict[str, Any]:
        """Procesa una escena individual a través del pipeline.

        Pipeline por escena:
            1. Audio: Genera TTS si hay texto
            2. Moho: Anima personaje con lip-sync si hay character
            3. Blender: Compone escena final

        Args:
            scene: Scene a procesar

        Returns:
            Dict con resultados de cada engine
        """
        scene_id = scene.id
        duration = scene.duration_seconds
        results: dict[str, Any] = {
            "scene_id": scene_id,
            "duration": duration,
        }

        logger.info(f"Processing scene: {scene_id}")

        # ==== PHASE 1: AUDIO ====
        self.progress.update(scene_id, "audio")
        self._notify_progress()

        audio_path: Path | None = None
        if scene.audio:
            audio_result = self.audio_engine.process(
                scene.audio,
                scene_id=scene_id,
            )
            audio_path = audio_result.output_path
            duration = audio_result.duration
            results["audio"] = {
                "path": str(audio_path) if audio_path else None,
                "duration": duration,
            }
            logger.debug(f"Audio generated: {audio_path} ({duration}s)")

        # ==== PHASE 2: MOHO (Character Animation) ====
        self.progress.update(scene_id, "moho")
        self._notify_progress()

        moho_frames_dir: Path | None = None
        if scene.character and audio_path:
            moho_config = MohoConfig(
                scene_id=scene_id,
                character=scene.character,
                audio_path=audio_path,
                output_dir=self._moho_dir / scene_id,
                duration=duration,
                expression=scene.character.expression,
                fps=self.spec.output.fps,
            )

            moho_result = self.moho_engine.process(moho_config)
            moho_frames_dir = moho_result.output_path
            results["moho"] = {
                "frames_dir": str(moho_frames_dir) if moho_frames_dir else None,
                "lip_sync": moho_result.metadata.get("lip_sync_frames") if moho_result.metadata else 0,
            }
            logger.debug(f"Moho animation: {moho_frames_dir}")

        # ==== PHASE 3: BLENDER (Scene Composition) ====
        self.progress.update(scene_id, "blender")
        self._notify_progress()

        # Determinar color de fondo
        background_color = "#1E3A5F"  # Default
        if scene.background:
            if scene.background.color:
                background_color = scene.background.color

        # Determinar posición de personaje
        character_position = "center"
        if scene.character:
            character_position = scene.character.position

        blender_config = BlenderSceneConfig(
            scene_id=scene_id,
            output_dir=self._blender_dir / scene_id,
            resolution=(self.spec.output.width, self.spec.output.height),
            fps=self.spec.output.fps,
            duration=duration,
            background_color=background_color,
            background_image=scene.background.image if scene.background else None,
            moho_frames_dir=moho_frames_dir,
            audio_path=audio_path,
            character_position=character_position,
        )

        blender_result = self.blender_engine.process(blender_config)
        results["blender"] = {
            "video_path": str(blender_result.output_path) if blender_result.output_path else None,
        }
        results["final_video"] = blender_result.output_path
        logger.debug(f"Blender composition: {blender_result.output_path}")

        return results

    def _compose_video(
        self,
        scene_results: list[dict[str, Any]],
        output_path: Path,
    ) -> Path:
        """Compone el video final concatenando escenas renderizadas.

        Args:
            scene_results: Lista de resultados por escena
            output_path: Path para el video final

        Returns:
            Path al video final

        Raises:
            ValueError: Si no hay escenas válidas
            subprocess.CalledProcessError: Si FFmpeg falla
        """
        output_config = self.spec.output
        fps = output_config.fps

        # Filtrar escenas con video válido
        valid_videos = [
            r["final_video"]
            for r in scene_results
            if r.get("final_video") and Path(r["final_video"]).exists()
        ]

        if not valid_videos:
            # Fallback: crear video con placeholder para cada escena
            logger.warning("No valid scene videos, creating fallback")
            return self._create_fallback_video(scene_results, output_path)

        # Crear archivo de concatenación
        concat_file = self._temp_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for video_path in valid_videos:
                f.write(f"file '{video_path}'\n")

        # Concatenar con FFmpeg
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-r", str(fps),
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info(f"Composing final video with FFmpeg")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                result.stdout,
                result.stderr,
            )

        return output_path

    def _create_fallback_video(
        self,
        scene_results: list[dict[str, Any]],
        output_path: Path,
    ) -> Path:
        """Crea un video fallback con colores sólidos y audio.

        Usado cuando los engines principales no están disponibles.

        Args:
            scene_results: Resultados de escenas con audio
            output_path: Path para el video

        Returns:
            Path al video generado
        """
        output_config = self.spec.output
        width = output_config.width
        height = output_config.height
        fps = output_config.fps

        segments: list[Path] = []

        for i, (result, scene) in enumerate(zip(scene_results, self.spec.scenes)):
            duration = result["duration"]
            audio_path = result.get("audio", {}).get("path")

            # Color de fondo
            bg_color = "0x1E3A5F"
            if scene.background and scene.background.color:
                bg_color = scene.background.color.replace("#", "0x")

            segment_path = self._output_dir / f"segment_{i}.mp4"

            if audio_path and Path(audio_path).exists():
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c={bg_color}:s={width}x{height}:r={fps}:d={duration}",
                    "-i", audio_path,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-shortest",
                    str(segment_path),
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c={bg_color}:s={width}x{height}:r={fps}:d={duration}",
                    "-c:v", "libx264",
                    "-an",
                    str(segment_path),
                ]

            subprocess.run(cmd, capture_output=True, check=True)
            segments.append(segment_path)

        # Concatenar segmentos
        if segments:
            concat_file = self._temp_dir / "fallback_concat.txt"
            with open(concat_file, "w") as f:
                for seg in segments:
                    f.write(f"file '{seg}'\n")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-c:a", "aac",
                str(output_path),
            ]

            subprocess.run(cmd, capture_output=True, check=True)

        return output_path

    def cleanup(self) -> None:
        """Limpia archivos temporales."""
        import shutil

        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)
            logger.debug(f"Cleaned up temp directory: {self._temp_dir}")

    def __enter__(self) -> "Orchestrator":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - limpia archivos temporales."""
        self.cleanup()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def render_spec(
    spec: AnimationSpec,
    output_path: Path | str,
    project_manager: ProjectManager | None = None,
    progress_callback: Callable[[RenderProgress], None] | None = None,
) -> Path:
    """Función de conveniencia para renderizar un spec.

    Args:
        spec: AnimationSpec a renderizar
        output_path: Path para el video de salida
        project_manager: Gestor de proyectos opcional
        progress_callback: Callback opcional para progreso

    Returns:
        Path al video generado
    """
    output_path = Path(output_path)

    with Orchestrator(spec, project_manager) as orch:
        if progress_callback:
            orch.on_progress(progress_callback)
        return orch.render(output_path)


def render_yaml(
    yaml_path: Path | str,
    output_path: Path | str | None = None,
    progress_callback: Callable[[RenderProgress], None] | None = None,
) -> Path:
    """Función de conveniencia para renderizar desde archivo YAML.

    Args:
        yaml_path: Path al archivo YAML del spec
        output_path: Path para el video (default: junto al YAML)
        progress_callback: Callback opcional para progreso

    Returns:
        Path al video generado
    """
    yaml_path = Path(yaml_path)
    spec = AnimationSpec.from_yaml(yaml_path)

    if output_path is None:
        output_path = yaml_path.parent / f"{yaml_path.stem}.mp4"
    else:
        output_path = Path(output_path)

    return render_spec(spec, output_path, progress_callback=progress_callback)
