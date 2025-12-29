"""Moho Engine para ANIMATR.

Este engine integra con Moho Pro para animación de personajes 2D.
Utiliza Lua scripting para controlar Moho headless y generar frames.
"""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from animatr.engines.base import Engine, EngineResult
from animatr.schema import AudioConfig, Character


@dataclass
class MohoConfig:
    """Configuración para el Moho Engine."""

    character: Character
    audio_path: Path | None = None
    duration: float = 5.0
    fps: int = 30
    width: int = 1920
    height: int = 1080
    output_format: str = "png"  # png sequence o mov


@dataclass
class LipSyncData:
    """Datos de lip-sync extraídos del audio."""

    phonemes: list[dict[str, Any]]  # [{time: float, phoneme: str, duration: float}]
    duration: float
    sample_rate: int = 44100


@dataclass
class MohoResult(EngineResult):
    """Resultado específico del Moho Engine."""

    frames_dir: Path | None = None
    frame_count: int = 0
    lip_sync_applied: bool = False


class MohoEngine(Engine):
    """Engine para animación de personajes con Moho Pro.

    Moho Pro debe estar instalado y la variable MOHO_PATH debe apuntar
    al ejecutable. En macOS típicamente:
    /Applications/Moho Pro 14/Moho Pro 14.app/Contents/MacOS/Moho Pro 14
    """

    # Mapeo de fonemas a poses de Moho (visemes)
    PHONEME_TO_VISEME = {
        # Vocales
        "AA": "mouth_open",
        "AE": "mouth_open",
        "AH": "mouth_open",
        "AO": "mouth_round",
        "AW": "mouth_round",
        "AY": "mouth_wide",
        "EH": "mouth_wide",
        "ER": "mouth_round",
        "EY": "mouth_wide",
        "IH": "mouth_smile",
        "IY": "mouth_smile",
        "OW": "mouth_round",
        "OY": "mouth_round",
        "UH": "mouth_round",
        "UW": "mouth_round",
        # Consonantes
        "B": "mouth_closed",
        "CH": "mouth_narrow",
        "D": "mouth_narrow",
        "DH": "mouth_narrow",
        "F": "mouth_f",
        "G": "mouth_narrow",
        "HH": "mouth_open",
        "JH": "mouth_narrow",
        "K": "mouth_narrow",
        "L": "mouth_l",
        "M": "mouth_closed",
        "N": "mouth_narrow",
        "NG": "mouth_narrow",
        "P": "mouth_closed",
        "R": "mouth_round",
        "S": "mouth_narrow",
        "SH": "mouth_narrow",
        "T": "mouth_narrow",
        "TH": "mouth_th",
        "V": "mouth_f",
        "W": "mouth_round",
        "Y": "mouth_smile",
        "Z": "mouth_narrow",
        "ZH": "mouth_narrow",
        # Silencio
        "SIL": "mouth_rest",
        "SP": "mouth_rest",
    }

    # Mapeo de expresiones a acciones de Moho
    EXPRESSION_ACTIONS = {
        "neutral": {"brows": 0, "eyes": 0, "mouth_curve": 0},
        "happy": {"brows": 0.2, "eyes": 0.1, "mouth_curve": 0.5},
        "sad": {"brows": -0.3, "eyes": -0.1, "mouth_curve": -0.4},
        "angry": {"brows": -0.5, "eyes": 0.2, "mouth_curve": -0.2},
        "surprised": {"brows": 0.6, "eyes": 0.4, "mouth_curve": 0.1},
        "thinking": {"brows": 0.3, "eyes": -0.2, "mouth_curve": 0},
        "excited": {"brows": 0.4, "eyes": 0.3, "mouth_curve": 0.6},
    }

    def __init__(self) -> None:
        self._temp_dir = Path(tempfile.mkdtemp(prefix="animatr_moho_"))
        self._moho_path = self._find_moho()

    def _find_moho(self) -> Path | None:
        """Encuentra el ejecutable de Moho Pro."""
        # Buscar en variable de entorno primero
        env_path = os.environ.get("MOHO_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Ubicaciones comunes en macOS
        mac_paths = [
            "/Applications/Moho Pro 14/Moho Pro 14.app/Contents/MacOS/Moho Pro 14",
            "/Applications/Moho Pro 13.5/Moho Pro 13.5.app/Contents/MacOS/Moho Pro 13.5",
            "/Applications/Moho Pro 13/Moho Pro 13.app/Contents/MacOS/Moho Pro 13",
        ]

        for path in mac_paths:
            if Path(path).exists():
                return Path(path)

        # Ubicaciones en Windows
        win_paths = [
            "C:/Program Files/Smith Micro/Moho Pro 14/Moho Pro 14.exe",
            "C:/Program Files/Smith Micro/Moho Pro 13.5/Moho Pro 13.5.exe",
        ]

        for path in win_paths:
            if Path(path).exists():
                return Path(path)

        return None

    def process(self, config: MohoConfig) -> MohoResult:
        """Procesa una configuración de personaje y genera frames animados."""
        if not self._moho_path:
            raise RuntimeError(
                "Moho Pro no encontrado. Instala Moho Pro y configura MOHO_PATH."
            )

        # Crear directorio para frames
        frames_dir = self._temp_dir / f"frames_{config.character.asset.replace('/', '_')}"
        frames_dir.mkdir(exist_ok=True)

        # Extraer lip-sync si hay audio
        lip_sync_data = None
        if config.audio_path and config.audio_path.exists():
            lip_sync_data = self._extract_lip_sync(config.audio_path)

        # Generar script Lua para Moho
        lua_script = self._generate_lua_script(
            config=config,
            lip_sync_data=lip_sync_data,
            output_dir=frames_dir,
        )

        # Guardar script
        script_path = self._temp_dir / "animate.lua"
        script_path.write_text(lua_script)

        # Ejecutar Moho
        success = self._run_moho(
            project_path=Path(config.character.asset),
            script_path=script_path,
            output_dir=frames_dir,
            config=config,
        )

        if not success:
            # Fallback: generar frames placeholder
            self._generate_placeholder_frames(frames_dir, config)

        frame_count = len(list(frames_dir.glob("*.png")))

        return MohoResult(
            scene_id=f"moho_{config.character.asset}",
            output_path=frames_dir,
            duration=config.duration,
            frames_dir=frames_dir,
            frame_count=frame_count,
            lip_sync_applied=lip_sync_data is not None,
            metadata={
                "character": config.character.asset,
                "expression": config.character.expression,
                "fps": config.fps,
            },
        )

    def validate(self, config: MohoConfig) -> bool:
        """Valida la configuración del engine."""
        if not config.character:
            return False

        asset_path = Path(config.character.asset)
        if not asset_path.suffix in (".moho", ".mohoproj", ".anme"):
            return False

        return True

    def _extract_lip_sync(self, audio_path: Path) -> LipSyncData | None:
        """Extrae datos de lip-sync del audio.

        Usa análisis de audio para generar fonemas aproximados.
        Para producción, se recomienda usar Rhubarb Lip Sync o similar.
        """
        try:
            # Intentar usar Rhubarb si está disponible
            rhubarb_path = shutil.which("rhubarb")
            if rhubarb_path:
                return self._extract_with_rhubarb(audio_path)

            # Fallback: análisis básico de energía
            return self._extract_basic_lip_sync(audio_path)

        except Exception as e:
            print(f"⚠️ Error extrayendo lip-sync: {e}")
            return None

    def _extract_with_rhubarb(self, audio_path: Path) -> LipSyncData:
        """Usa Rhubarb Lip Sync para extraer fonemas precisos."""
        output_path = self._temp_dir / "lip_sync.json"

        cmd = [
            "rhubarb",
            str(audio_path),
            "-o", str(output_path),
            "-f", "json",
            "--machineReadable",
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"Rhubarb falló: {result.stderr.decode()}")

        data = json.loads(output_path.read_text())

        phonemes = []
        for cue in data.get("mouthCues", []):
            phonemes.append({
                "time": cue["start"],
                "phoneme": cue["value"],
                "duration": cue["end"] - cue["start"],
            })

        return LipSyncData(
            phonemes=phonemes,
            duration=data.get("metadata", {}).get("duration", 0),
        )

    def _extract_basic_lip_sync(self, audio_path: Path) -> LipSyncData:
        """Análisis básico de audio para lip-sync aproximado."""
        # Usar FFmpeg para obtener volumen por frame
        output_path = self._temp_dir / "volume.txt"

        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-af", "volumedetect",
            "-f", "null",
            "-",
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=60)

        # Obtener duración
        probe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]

        duration_result = subprocess.run(probe_cmd, capture_output=True, timeout=30)
        duration = float(duration_result.stdout.decode().strip() or "5.0")

        # Generar fonemas básicos basados en duración
        # En producción, esto debería ser análisis real de audio
        phonemes = []
        interval = 0.1  # 100ms por fonema
        current_time = 0.0

        basic_sequence = ["SIL", "AA", "M", "AA", "SIL"]

        while current_time < duration:
            for phoneme in basic_sequence:
                if current_time >= duration:
                    break
                phonemes.append({
                    "time": current_time,
                    "phoneme": phoneme,
                    "duration": interval,
                })
                current_time += interval

        return LipSyncData(
            phonemes=phonemes,
            duration=duration,
        )

    def _generate_lua_script(
        self,
        config: MohoConfig,
        lip_sync_data: LipSyncData | None,
        output_dir: Path,
    ) -> str:
        """Genera el script Lua para controlar Moho."""
        total_frames = int(config.duration * config.fps)

        # Convertir lip-sync a keyframes
        lip_sync_keyframes = ""
        if lip_sync_data:
            for phoneme_data in lip_sync_data.phonemes:
                frame = int(phoneme_data["time"] * config.fps)
                viseme = self.PHONEME_TO_VISEME.get(
                    phoneme_data["phoneme"], "mouth_rest"
                )
                lip_sync_keyframes += f'    {{frame = {frame}, viseme = "{viseme}"}},\n'

        # Obtener datos de expresión
        expression_data = self.EXPRESSION_ACTIONS.get(
            config.character.expression, self.EXPRESSION_ACTIONS["neutral"]
        )

        script = f'''-- ANIMATR Moho Animation Script
-- Auto-generated for: {config.character.asset}

-- Configuración
local CONFIG = {{
    output_dir = "{output_dir}",
    total_frames = {total_frames},
    fps = {config.fps},
    width = {config.width},
    height = {config.height},
    expression = "{config.character.expression}",
}}

-- Datos de expresión
local EXPRESSION = {{
    brows = {expression_data["brows"]},
    eyes = {expression_data["eyes"]},
    mouth_curve = {expression_data["mouth_curve"]},
}}

-- Keyframes de lip-sync
local LIP_SYNC = {{
{lip_sync_keyframes}}}

-- Mapeo de visemes a valores de bone
local VISEME_VALUES = {{
    mouth_rest = 0,
    mouth_closed = 0.1,
    mouth_open = 0.8,
    mouth_round = 0.6,
    mouth_wide = 0.7,
    mouth_smile = 0.5,
    mouth_narrow = 0.3,
    mouth_f = 0.4,
    mouth_l = 0.35,
    mouth_th = 0.45,
}}

-- Función principal de animación
function AnimateCharacter(moho)
    local doc = moho.document
    local layer = moho:LayerAsGroup(moho.layer)

    if layer == nil then
        print("Error: No se encontró el layer del personaje")
        return
    end

    -- Aplicar expresión base
    ApplyExpression(moho, layer, EXPRESSION)

    -- Aplicar lip-sync frame por frame
    for i, keyframe in ipairs(LIP_SYNC) do
        local frame = keyframe.frame
        local viseme = keyframe.viseme
        local value = VISEME_VALUES[viseme] or 0

        ApplyMouthShape(moho, layer, frame, value)
    end

    -- Renderizar frames
    RenderFrames(moho, doc)
end

function ApplyExpression(moho, layer, expr)
    -- Buscar bones de expresión
    local skeleton = moho:LayerAsSkeleton(layer)
    if skeleton == nil then return end

    local skel = skeleton:Skeleton()
    if skel == nil then return end

    for i = 0, skel:CountBones() - 1 do
        local bone = skel:Bone(i)
        local name = bone:Name()

        if string.find(name, "brow") then
            -- Aplicar valor a cejas
            local angle = expr.brows * 0.3
            bone.fAngle:SetValue(0, angle)
        elseif string.find(name, "eye") then
            -- Aplicar valor a ojos
            local scale = 1 + expr.eyes * 0.2
            bone.fScale:SetValue(0, scale)
        end
    end
end

function ApplyMouthShape(moho, layer, frame, value)
    local skeleton = moho:LayerAsSkeleton(layer)
    if skeleton == nil then return end

    local skel = skeleton:Skeleton()
    if skel == nil then return end

    for i = 0, skel:CountBones() - 1 do
        local bone = skel:Bone(i)
        local name = bone:Name()

        if string.find(name:lower(), "mouth") or string.find(name:lower(), "jaw") then
            -- Aplicar apertura de boca
            local currentAngle = bone.fAngle:GetValue(0)
            local targetAngle = currentAngle + (value * 0.5)
            bone.fAngle:SetValue(frame, targetAngle)
        end
    end
end

function RenderFrames(moho, doc)
    local renderSettings = doc:RenderSettings()

    renderSettings.fFormat = MOHO.RIF_PNG
    renderSettings.fWidth = CONFIG.width
    renderSettings.fHeight = CONFIG.height
    renderSettings.fStartFrame = 0
    renderSettings.fEndFrame = CONFIG.total_frames - 1
    renderSettings.fFrameRate = CONFIG.fps

    for frame = 0, CONFIG.total_frames - 1 do
        local filename = string.format("%s/frame_%05d.png", CONFIG.output_dir, frame)
        doc:RenderFrame(frame, filename, renderSettings)
    end
end

-- Ejecutar
AnimateCharacter(moho)
print("Animación completada: " .. CONFIG.total_frames .. " frames")
'''
        return script

    def _run_moho(
        self,
        project_path: Path,
        script_path: Path,
        output_dir: Path,
        config: MohoConfig,
    ) -> bool:
        """Ejecuta Moho Pro con el script de animación."""
        if not self._moho_path:
            return False

        try:
            # Moho Pro command line rendering
            cmd = [
                str(self._moho_path),
                "-r",  # Render mode
                str(project_path),
                "-script", str(script_path),
                "-start", "0",
                "-end", str(int(config.duration * config.fps) - 1),
                "-format", "png",
                "-output", str(output_dir / "frame_"),
                "-width", str(config.width),
                "-height", str(config.height),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600,  # 10 minutos máximo
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("⚠️ Moho render timeout")
            return False
        except Exception as e:
            print(f"⚠️ Error ejecutando Moho: {e}")
            return False

    def _generate_placeholder_frames(
        self,
        output_dir: Path,
        config: MohoConfig,
    ) -> None:
        """Genera frames placeholder cuando Moho no está disponible."""
        try:
            total_frames = int(config.duration * config.fps)

            # Usar FFmpeg para generar frames de color sólido con texto
            for i in range(min(total_frames, 300)):  # Limitar a 300 frames
                output_path = output_dir / f"frame_{i:05d}.png"

                # Color basado en posición del personaje
                colors = {
                    "left": "0x3498db",
                    "center": "0x2ecc71",
                    "right": "0xe74c3c",
                }
                color = colors.get(config.character.position, "0x9b59b6")

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "lavfi",
                    "-i", f"color=c={color}:s={config.width}x{config.height}:d=0.04",
                    "-vframes", "1",
                    "-vf", f"drawtext=text='Frame {i} - {config.character.expression}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                    str(output_path),
                ]

                subprocess.run(cmd, capture_output=True, timeout=10)

        except Exception as e:
            print(f"⚠️ Error generando placeholders: {e}")


class MohoAssetManager:
    """Gestiona assets de Moho (personajes, props, backgrounds)."""

    def __init__(self, assets_dir: Path | None = None) -> None:
        self.assets_dir = assets_dir or Path("assets/moho")

    def list_characters(self) -> list[dict[str, Any]]:
        """Lista todos los personajes disponibles."""
        characters = []

        if not self.assets_dir.exists():
            return characters

        for path in self.assets_dir.glob("**/*.moho"):
            characters.append({
                "name": path.stem,
                "path": str(path),
                "type": "character",
            })

        return characters

    def get_character_info(self, asset_path: str) -> dict[str, Any] | None:
        """Obtiene información sobre un personaje."""
        path = Path(asset_path)

        if not path.exists():
            return None

        return {
            "name": path.stem,
            "path": str(path),
            "size": path.stat().st_size,
            "type": "moho_project",
        }
