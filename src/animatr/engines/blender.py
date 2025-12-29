"""Blender Engine para ANIMATR.

Este engine integra con Blender para composición de escenas,
cámaras, iluminación y render final.
"""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from animatr.engines.base import Engine, EngineResult
from animatr.schema import Background, Character


@dataclass
class BlenderSceneConfig:
    """Configuración para una escena de Blender."""

    scene_id: str
    duration: float
    width: int = 1920
    height: int = 1080
    fps: int = 30
    background: Background | None = None
    character_frames_dir: Path | None = None
    character_position: str = "center"
    audio_path: Path | None = None
    camera_motion: str = "static"  # static, pan, zoom, orbit


@dataclass
class BlenderResult(EngineResult):
    """Resultado específico del Blender Engine."""

    video_path: Path | None = None
    render_time: float = 0.0
    frame_count: int = 0


class BlenderEngine(Engine):
    """Engine para composición y render con Blender.

    Blender debe estar instalado y accesible vía CLI.
    """

    # Configuraciones de cámara predefinidas
    CAMERA_PRESETS = {
        "static": {
            "location": (0, -10, 2),
            "rotation": (80, 0, 0),
            "keyframes": [],
        },
        "pan_left": {
            "location": (0, -10, 2),
            "rotation": (80, 0, 0),
            "keyframes": [
                {"frame": 0, "location": (-2, -10, 2)},
                {"frame": -1, "location": (2, -10, 2)},  # -1 = último frame
            ],
        },
        "pan_right": {
            "location": (0, -10, 2),
            "rotation": (80, 0, 0),
            "keyframes": [
                {"frame": 0, "location": (2, -10, 2)},
                {"frame": -1, "location": (-2, -10, 2)},
            ],
        },
        "zoom_in": {
            "location": (0, -10, 2),
            "rotation": (80, 0, 0),
            "keyframes": [
                {"frame": 0, "location": (0, -12, 2.5)},
                {"frame": -1, "location": (0, -8, 1.5)},
            ],
        },
        "zoom_out": {
            "location": (0, -10, 2),
            "rotation": (80, 0, 0),
            "keyframes": [
                {"frame": 0, "location": (0, -8, 1.5)},
                {"frame": -1, "location": (0, -12, 2.5)},
            ],
        },
        "orbit": {
            "location": (0, -10, 2),
            "rotation": (80, 0, 0),
            "keyframes": [
                {"frame": 0, "rotation": (80, 0, -15)},
                {"frame": 0.5, "rotation": (80, 0, 15)},
                {"frame": -1, "rotation": (80, 0, -15)},
            ],
        },
    }

    # Posiciones de personaje en el espacio 3D
    CHARACTER_POSITIONS = {
        "left": (-3, 0, 0),
        "center": (0, 0, 0),
        "right": (3, 0, 0),
    }

    def __init__(self) -> None:
        self._temp_dir = Path(tempfile.mkdtemp(prefix="animatr_blender_"))
        self._blender_path = self._find_blender()

    def _find_blender(self) -> Path | None:
        """Encuentra el ejecutable de Blender."""
        # Variable de entorno
        env_path = os.environ.get("BLENDER_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Buscar en PATH
        blender_in_path = shutil.which("blender")
        if blender_in_path:
            return Path(blender_in_path)

        # Ubicaciones comunes en macOS
        mac_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender 4.0.app/Contents/MacOS/Blender",
            "/Applications/Blender 4.1.app/Contents/MacOS/Blender",
            "/Applications/Blender 4.2.app/Contents/MacOS/Blender",
        ]

        for path in mac_paths:
            if Path(path).exists():
                return Path(path)

        # Ubicaciones en Windows
        win_paths = [
            "C:/Program Files/Blender Foundation/Blender 4.0/blender.exe",
            "C:/Program Files/Blender Foundation/Blender 4.1/blender.exe",
            "C:/Program Files/Blender Foundation/Blender/blender.exe",
        ]

        for path in win_paths:
            if Path(path).exists():
                return Path(path)

        return None

    def process(self, config: BlenderSceneConfig) -> BlenderResult:
        """Procesa una escena y genera el video renderizado."""
        if not self._blender_path:
            # Fallback sin Blender
            return self._process_without_blender(config)

        # Generar script Python para Blender
        script_path = self._generate_blender_script(config)

        # Ejecutar Blender
        output_path = self._temp_dir / f"{config.scene_id}.mp4"
        success, render_time = self._run_blender(script_path, output_path)

        if not success:
            return self._process_without_blender(config)

        frame_count = int(config.duration * config.fps)

        return BlenderResult(
            scene_id=config.scene_id,
            output_path=output_path,
            duration=config.duration,
            video_path=output_path,
            render_time=render_time,
            frame_count=frame_count,
            metadata={
                "engine": "blender",
                "camera": config.camera_motion,
                "resolution": f"{config.width}x{config.height}",
            },
        )

    def validate(self, config: BlenderSceneConfig) -> bool:
        """Valida la configuración del engine."""
        if config.duration <= 0:
            return False
        if config.width <= 0 or config.height <= 0:
            return False
        if config.fps <= 0:
            return False
        return True

    def _generate_blender_script(self, config: BlenderSceneConfig) -> Path:
        """Genera el script Python para Blender."""
        total_frames = int(config.duration * config.fps)
        output_path = self._temp_dir / f"{config.scene_id}.mp4"

        # Obtener configuración de cámara
        camera_preset = self.CAMERA_PRESETS.get(
            config.camera_motion,
            self.CAMERA_PRESETS["static"]
        )

        # Obtener posición del personaje
        char_position = self.CHARACTER_POSITIONS.get(
            config.character_position,
            self.CHARACTER_POSITIONS["center"]
        )

        # Color de fondo
        bg_color = (0.1, 0.1, 0.15, 1.0)  # Default dark
        if config.background and config.background.color:
            hex_color = config.background.color.lstrip("#")
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            bg_color = (r, g, b, 1.0)

        # Imagen de fondo si existe
        bg_image_path = ""
        if config.background and config.background.image:
            bg_image_path = config.background.image

        # Frames del personaje si existen
        char_frames_path = ""
        if config.character_frames_dir and config.character_frames_dir.exists():
            char_frames_path = str(config.character_frames_dir)

        # Audio si existe
        audio_path = ""
        if config.audio_path and config.audio_path.exists():
            audio_path = str(config.audio_path)

        script = f'''
# ANIMATR Blender Scene Script
# Auto-generated for scene: {config.scene_id}

import bpy
import math
import os

# Limpiar escena
bpy.ops.wm.read_factory_settings(use_empty=True)

# Configuración
CONFIG = {{
    "scene_id": "{config.scene_id}",
    "duration": {config.duration},
    "fps": {config.fps},
    "width": {config.width},
    "height": {config.height},
    "total_frames": {total_frames},
    "output_path": "{output_path}",
    "bg_color": {bg_color},
    "bg_image": "{bg_image_path}",
    "char_frames": "{char_frames_path}",
    "char_position": {char_position},
    "audio_path": "{audio_path}",
}}

CAMERA_CONFIG = {{
    "location": {camera_preset["location"]},
    "rotation": {camera_preset["rotation"]},
    "keyframes": {json.dumps(camera_preset.get("keyframes", []))},
}}

def setup_scene():
    """Configura la escena básica."""
    scene = bpy.context.scene
    scene.render.resolution_x = CONFIG["width"]
    scene.render.resolution_y = CONFIG["height"]
    scene.render.fps = CONFIG["fps"]
    scene.frame_start = 1
    scene.frame_end = CONFIG["total_frames"]

    # Formato de salida
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.ffmpeg.audio_codec = 'AAC'
    scene.render.filepath = CONFIG["output_path"]

    # Color de fondo del mundo
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes["Background"]
    bg_node.inputs["Color"].default_value = CONFIG["bg_color"]

def setup_camera():
    """Configura la cámara con animación."""
    bpy.ops.object.camera_add(
        location=CAMERA_CONFIG["location"],
        rotation=(
            math.radians(CAMERA_CONFIG["rotation"][0]),
            math.radians(CAMERA_CONFIG["rotation"][1]),
            math.radians(CAMERA_CONFIG["rotation"][2])
        )
    )
    camera = bpy.context.active_object
    camera.name = "AnimatrCamera"
    bpy.context.scene.camera = camera

    # Aplicar keyframes de animación
    keyframes = eval(CAMERA_CONFIG["keyframes"]) if CAMERA_CONFIG["keyframes"] else []

    for kf in keyframes:
        frame = kf.get("frame", 0)
        if frame == -1:
            frame = CONFIG["total_frames"]
        elif frame < 1:
            frame = int(frame * CONFIG["total_frames"])

        if "location" in kf:
            camera.location = kf["location"]
            camera.keyframe_insert(data_path="location", frame=frame)

        if "rotation" in kf:
            camera.rotation_euler = (
                math.radians(kf["rotation"][0]),
                math.radians(kf["rotation"][1]),
                math.radians(kf["rotation"][2])
            )
            camera.keyframe_insert(data_path="rotation_euler", frame=frame)

def setup_lighting():
    """Configura iluminación de 3 puntos."""
    # Key light
    bpy.ops.object.light_add(type='AREA', location=(4, -4, 6))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 500
    key.data.size = 5

    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(-3, -3, 4))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 200
    fill.data.size = 3

    # Back light
    bpy.ops.object.light_add(type='AREA', location=(0, 4, 5))
    back = bpy.context.active_object
    back.name = "BackLight"
    back.data.energy = 300
    back.data.size = 4

def setup_background():
    """Configura el fondo de la escena."""
    if CONFIG["bg_image"] and os.path.exists(CONFIG["bg_image"]):
        # Crear plano con imagen de fondo
        bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 5, 0))
        bg_plane = bpy.context.active_object
        bg_plane.name = "Background"
        bg_plane.rotation_euler = (math.radians(90), 0, 0)

        # Material con imagen
        mat = bpy.data.materials.new("BackgroundMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Nodo de imagen
        img_node = nodes.new('ShaderNodeTexImage')
        img_node.image = bpy.data.images.load(CONFIG["bg_image"])

        # Conectar a BSDF
        bsdf = nodes["Principled BSDF"]
        links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 1.0

        bg_plane.data.materials.append(mat)

def setup_character():
    """Configura el personaje usando secuencia de frames."""
    if not CONFIG["char_frames"] or not os.path.exists(CONFIG["char_frames"]):
        # Crear placeholder
        bpy.ops.mesh.primitive_cube_add(size=2, location=CONFIG["char_position"])
        cube = bpy.context.active_object
        cube.name = "CharacterPlaceholder"
        return

    # Crear plano para la secuencia de imágenes
    bpy.ops.mesh.primitive_plane_add(
        size=4,
        location=(CONFIG["char_position"][0], CONFIG["char_position"][1], 2)
    )
    char_plane = bpy.context.active_object
    char_plane.name = "Character"

    # Material con secuencia de imágenes
    mat = bpy.data.materials.new("CharacterMaterial")
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Nodo de secuencia de imágenes
    img_node = nodes.new('ShaderNodeTexImage')

    # Cargar primer frame para obtener configuración
    frames_dir = CONFIG["char_frames"]
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])

    if frame_files:
        first_frame = os.path.join(frames_dir, frame_files[0])
        img = bpy.data.images.load(first_frame)
        img.source = 'SEQUENCE'
        img_node.image = img
        img_node.image_user.frame_duration = len(frame_files)
        img_node.image_user.frame_start = 1
        img_node.image_user.use_auto_refresh = True

    # Conectar a BSDF con transparencia
    bsdf = nodes["Principled BSDF"]
    links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(img_node.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 1.0

    char_plane.data.materials.append(mat)

def setup_audio():
    """Configura el audio de la escena."""
    if not CONFIG["audio_path"] or not os.path.exists(CONFIG["audio_path"]):
        return

    # Agregar strip de audio al VSE
    if not bpy.context.scene.sequence_editor:
        bpy.context.scene.sequence_editor_create()

    bpy.context.scene.sequence_editor.sequences.new_sound(
        name="Audio",
        filepath=CONFIG["audio_path"],
        channel=1,
        frame_start=1
    )

def render():
    """Ejecuta el render."""
    bpy.ops.render.render(animation=True)
    print(f"Render completado: {{CONFIG['output_path']}}")

# Ejecutar setup y render
print("ANIMATR Blender: Iniciando...")
setup_scene()
setup_camera()
setup_lighting()
setup_background()
setup_character()
setup_audio()
print("ANIMATR Blender: Configuración completa, iniciando render...")
render()
print("ANIMATR Blender: ¡Completado!")
'''

        script_path = self._temp_dir / f"{config.scene_id}_blender.py"
        script_path.write_text(script)
        return script_path

    def _run_blender(
        self,
        script_path: Path,
        output_path: Path,
    ) -> tuple[bool, float]:
        """Ejecuta Blender con el script generado."""
        import time

        if not self._blender_path:
            return False, 0.0

        start_time = time.time()

        try:
            cmd = [
                str(self._blender_path),
                "--background",
                "--python", str(script_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=1800,  # 30 minutos máximo
            )

            render_time = time.time() - start_time

            if result.returncode == 0 and output_path.exists():
                return True, render_time

            print(f"⚠️ Blender stderr: {result.stderr.decode()[:500]}")
            return False, render_time

        except subprocess.TimeoutExpired:
            print("⚠️ Blender render timeout")
            return False, time.time() - start_time
        except Exception as e:
            print(f"⚠️ Error ejecutando Blender: {e}")
            return False, 0.0

    def _process_without_blender(self, config: BlenderSceneConfig) -> BlenderResult:
        """Procesa la escena sin Blender usando FFmpeg."""
        output_path = self._temp_dir / f"{config.scene_id}.mp4"
        total_frames = int(config.duration * config.fps)

        # Color de fondo
        bg_color = "0x1a1a2e"
        if config.background and config.background.color:
            bg_color = config.background.color.replace("#", "0x")

        try:
            if config.character_frames_dir and config.character_frames_dir.exists():
                # Combinar frames del personaje con fondo
                frame_pattern = str(config.character_frames_dir / "frame_%05d.png")

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-framerate", str(config.fps),
                    "-i", frame_pattern,
                    "-f", "lavfi",
                    "-i", f"color=c={bg_color}:s={config.width}x{config.height}:r={config.fps}:d={config.duration}",
                    "-filter_complex", "[1:v][0:v]overlay=(W-w)/2:(H-h)/2",
                ]

                # Agregar audio si existe
                if config.audio_path and config.audio_path.exists():
                    cmd.extend(["-i", str(config.audio_path), "-c:a", "aac"])

                cmd.extend([
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                    str(output_path),
                ])

            else:
                # Solo generar video con fondo de color
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "lavfi",
                    "-i", f"color=c={bg_color}:s={config.width}x{config.height}:r={config.fps}:d={config.duration}",
                ]

                if config.audio_path and config.audio_path.exists():
                    cmd.extend([
                        "-i", str(config.audio_path),
                        "-c:a", "aac",
                        "-shortest",
                    ])

                cmd.extend([
                    "-c:v", "libx264",
                    str(output_path),
                ])

            subprocess.run(cmd, check=True, capture_output=True, timeout=300)

            return BlenderResult(
                scene_id=config.scene_id,
                output_path=output_path,
                duration=config.duration,
                video_path=output_path,
                render_time=0.0,
                frame_count=total_frames,
                metadata={
                    "engine": "ffmpeg_fallback",
                    "resolution": f"{config.width}x{config.height}",
                },
            )

        except Exception as e:
            print(f"⚠️ Error en fallback FFmpeg: {e}")
            return BlenderResult(
                scene_id=config.scene_id,
                output_path=None,
                duration=config.duration,
                video_path=None,
                render_time=0.0,
                frame_count=0,
                metadata={"error": str(e)},
            )


class BlenderAssetManager:
    """Gestiona assets de Blender (escenas, materiales, etc.)."""

    def __init__(self, assets_dir: Path | None = None) -> None:
        self.assets_dir = assets_dir or Path("assets/blender")

    def list_scenes(self) -> list[dict[str, Any]]:
        """Lista todas las escenas disponibles."""
        scenes = []

        if not self.assets_dir.exists():
            return scenes

        for path in self.assets_dir.glob("**/*.blend"):
            scenes.append({
                "name": path.stem,
                "path": str(path),
                "type": "blender_scene",
            })

        return scenes

    def list_backgrounds(self) -> list[dict[str, Any]]:
        """Lista fondos disponibles."""
        backgrounds = []
        bg_dir = self.assets_dir / "backgrounds"

        if not bg_dir.exists():
            return backgrounds

        for path in bg_dir.glob("*"):
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".hdr", ".exr"):
                backgrounds.append({
                    "name": path.stem,
                    "path": str(path),
                    "type": "background",
                })

        return backgrounds
