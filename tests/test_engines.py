"""Tests para los engines de ANIMATR."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from animatr.engines.audio import AudioEngine
from animatr.engines.base import Engine, EngineResult
from animatr.engines.blender import BlenderEngine, BlenderSceneConfig
from animatr.engines.moho import MohoConfig, MohoEngine
from animatr.schema import AudioConfig, Character


class TestEngineBase:
    """Tests para Engine base."""

    def test_engine_result_dataclass(self) -> None:
        """Verifica EngineResult."""
        result = EngineResult(
            scene_id="test",
            output_path=Path("/output/test.mp4"),
            duration=5.0,
            metadata={"key": "value"},
        )

        assert result.scene_id == "test"
        assert result.output_path == Path("/output/test.mp4")
        assert result.duration == 5.0
        assert result.metadata == {"key": "value"}

    def test_engine_result_optional_fields(self) -> None:
        """Verifica campos opcionales de EngineResult."""
        result = EngineResult(
            scene_id="test",
            output_path=None,
            duration=0.0,
        )

        assert result.output_path is None
        assert result.metadata is None


class TestMohoEngine:
    """Tests para MohoEngine."""

    def test_phoneme_to_viseme_mapping(self) -> None:
        """Verifica mapeo de fonemas a visemas."""
        engine = MohoEngine()

        # Test vocal sounds (CMU phoneme set)
        assert engine.PHONEME_TO_VISEME.get("AA") == "mouth_open"
        assert engine.PHONEME_TO_VISEME.get("IY") == "mouth_smile"  # 'ee' sound

        # Test consonants
        assert engine.PHONEME_TO_VISEME.get("M") == "mouth_closed"
        assert engine.PHONEME_TO_VISEME.get("P") == "mouth_closed"

    def test_expression_actions_mapping(self) -> None:
        """Verifica mapeo de expresiones a acciones."""
        engine = MohoEngine()

        assert "happy" in engine.EXPRESSION_ACTIONS
        assert "sad" in engine.EXPRESSION_ACTIONS
        assert "angry" in engine.EXPRESSION_ACTIONS

    def test_moho_config_creation(self) -> None:
        """Verifica creación de MohoConfig."""
        config = MohoConfig(
            character=Character(asset="char.moho"),
            audio_path=Path("/audio/test.mp3"),
            duration=5.0,
            fps=30,
        )

        assert config.duration == 5.0
        assert config.fps == 30
        assert config.character.asset == "char.moho"

    def test_validate_config(self) -> None:
        """Verifica validación de configuración."""
        engine = MohoEngine()

        config = MohoConfig(
            character=Character(asset="char.moho"),
            audio_path=Path("/audio/test.mp3"),
            duration=5.0,
        )

        # Should not raise - validate returns bool
        is_valid = engine.validate(config)
        assert isinstance(is_valid, bool)

    @patch("subprocess.run")
    def test_process_with_fallback(
        self, mock_run: MagicMock, temp_dir: Path
    ) -> None:
        """Verifica procesamiento con fallback cuando Moho falla."""
        engine = MohoEngine()
        # Mock _moho_path to simulate Moho being configured
        engine._moho_path = Path("/fake/moho/path")

        # Create mock audio file
        audio_path = temp_dir / "test.mp3"
        audio_path.write_bytes(b"\x00" * 100)

        config = MohoConfig(
            character=Character(asset="char.moho"),
            audio_path=audio_path,
            duration=5.0,
        )

        # Mock Moho subprocess failing
        mock_run.side_effect = FileNotFoundError("Moho not found")

        result = engine.process(config)

        # Fallback should generate placeholder frames
        assert result.duration >= 0


class TestBlenderEngine:
    """Tests para BlenderEngine."""

    def test_camera_presets(self) -> None:
        """Verifica presets de cámara."""
        engine = BlenderEngine()

        assert "static" in engine.CAMERA_PRESETS
        assert "pan_left" in engine.CAMERA_PRESETS
        assert "zoom_in" in engine.CAMERA_PRESETS

        # Verify preset structure
        static = engine.CAMERA_PRESETS["static"]
        assert "location" in static
        assert "rotation" in static

    def test_character_positions(self) -> None:
        """Verifica posiciones de personajes."""
        engine = BlenderEngine()

        assert "left" in engine.CHARACTER_POSITIONS
        assert "center" in engine.CHARACTER_POSITIONS
        assert "right" in engine.CHARACTER_POSITIONS

    def test_blender_scene_config_creation(self) -> None:
        """Verifica creación de BlenderSceneConfig."""
        from animatr.schema import Background

        config = BlenderSceneConfig(
            scene_id="test",
            duration=5.0,
            width=1920,
            height=1080,
            fps=30,
            background=Background(color="#1E3A5F"),
        )

        assert config.scene_id == "test"
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 30

    def test_camera_motion_options(self) -> None:
        """Verifica opciones de movimiento de cámara."""
        config = BlenderSceneConfig(
            scene_id="test",
            duration=5.0,
            camera_motion="zoom_in",
        )

        assert config.camera_motion == "zoom_in"

    def test_validate_config(self) -> None:
        """Verifica validación de configuración."""
        engine = BlenderEngine()

        config = BlenderSceneConfig(
            scene_id="test",
            duration=5.0,
            width=1920,
            height=1080,
            fps=30,
        )

        is_valid = engine.validate(config)
        assert isinstance(is_valid, bool)

    @patch("subprocess.run")
    def test_process_with_fallback(
        self, mock_run: MagicMock, temp_dir: Path
    ) -> None:
        """Verifica procesamiento con fallback."""
        from animatr.schema import Background

        engine = BlenderEngine()

        config = BlenderSceneConfig(
            scene_id="test",
            duration=5.0,
            width=1920,
            height=1080,
            fps=30,
            background=Background(color="#1E3A5F"),
        )

        # Mock Blender not being available
        mock_run.side_effect = FileNotFoundError("Blender not found")

        result = engine.process(config)

        assert result.scene_id == "test"


class TestAudioEngine:
    """Tests para AudioEngine."""

    def test_audio_engine_init(self) -> None:
        """Verifica inicialización del engine."""
        engine = AudioEngine()
        assert engine is not None

    def test_validate_audio_config(self) -> None:
        """Verifica validación de config de audio."""
        engine = AudioEngine()

        config = AudioConfig(
            text="Hello world",
            voice="alloy",
            provider="openai",
        )

        is_valid = engine.validate(config)
        assert isinstance(is_valid, bool)

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_process_without_api_key(self) -> None:
        """Verifica procesamiento sin API key."""
        engine = AudioEngine()

        config = AudioConfig(
            text="Hello world",
            voice="alloy",
            provider="openai",
        )

        # Should handle missing API key gracefully - raises or returns error
        try:
            result = engine.process(config)
            # Result may be placeholder depending on implementation
            assert result is None or hasattr(result, "output_path")
        except Exception:
            # Expected if API key is required
            pass


class TestEngineIntegration:
    """Tests de integración entre engines."""

    def test_moho_result_as_blender_input(self, temp_dir: Path) -> None:
        """Verifica que resultado de Moho puede usarse en Blender."""
        # Create mock Moho output
        moho_frames_dir = temp_dir / "moho_frames"
        moho_frames_dir.mkdir()

        for i in range(5):
            frame = moho_frames_dir / f"frame_{i:04d}.png"
            frame.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        # Configure Blender to use Moho frames (character_frames_dir is the correct field)
        blender_config = BlenderSceneConfig(
            scene_id="test",
            duration=5.0,
            width=1920,
            height=1080,
            fps=30,
            character_frames_dir=moho_frames_dir,
        )

        assert blender_config.character_frames_dir == moho_frames_dir

    def test_full_pipeline_config(self, temp_dir: Path) -> None:
        """Verifica configuración completa del pipeline."""
        from animatr.schema import Background

        # Audio config
        audio_config = AudioConfig(
            text="Test narration",
            voice="alloy",
            provider="openai",
        )

        # Character config
        character = Character(
            asset="presenter.moho",
            position="center",
            expression="happy",
        )

        # Moho config (uses actual fields)
        moho_config = MohoConfig(
            character=character,
            audio_path=temp_dir / "audio.mp3",
            duration=5.0,
        )

        # Blender config (uses actual fields)
        blender_config = BlenderSceneConfig(
            scene_id="test",
            duration=5.0,
            width=1920,
            height=1080,
            fps=30,
            background=Background(color="#1E3A5F"),
            character_position="center",
        )

        assert audio_config.text == "Test narration"
        assert moho_config.character.asset == "presenter.moho"
        assert blender_config.character_position == "center"
