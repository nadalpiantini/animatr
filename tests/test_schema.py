"""Tests para los modelos Pydantic de ANIMATR."""

import tempfile
from pathlib import Path

import pytest
import yaml

from animatr.schema import (
    AnimationSpec,
    AudioConfig,
    Background,
    Character,
    OutputConfig,
    Scene,
)


class TestOutputConfig:
    def test_defaults(self):
        config = OutputConfig()
        assert config.format == "mp4"
        assert config.resolution == "1920x1080"
        assert config.fps == 30

    def test_dimensions(self):
        config = OutputConfig(resolution="1280x720")
        assert config.width == 1280
        assert config.height == 720

    def test_fps_validation(self):
        with pytest.raises(ValueError):
            OutputConfig(fps=0)
        with pytest.raises(ValueError):
            OutputConfig(fps=200)


class TestAudioConfig:
    def test_required_text(self):
        config = AudioConfig(text="Hola mundo")
        assert config.text == "Hola mundo"
        assert config.voice == "alloy"
        assert config.provider == "openai"

    def test_empty_text_fails(self):
        with pytest.raises(ValueError):
            AudioConfig(text="")

    def test_speed_bounds(self):
        with pytest.raises(ValueError):
            AudioConfig(text="test", speed=0.1)
        with pytest.raises(ValueError):
            AudioConfig(text="test", speed=3.0)


class TestCharacter:
    def test_defaults(self):
        char = Character(asset="./char.moho")
        assert char.position == "center"
        assert char.expression == "neutral"
        assert char.scale == 1.0

    def test_scale_bounds(self):
        with pytest.raises(ValueError):
            Character(asset="./char.moho", scale=0.05)


class TestScene:
    def test_duration_parsing(self):
        scene = Scene(id="intro", duration="5s")
        assert scene.duration_seconds == 5.0

        scene = Scene(id="intro", duration="2.5s")
        assert scene.duration_seconds == 2.5

    def test_invalid_duration(self):
        with pytest.raises(ValueError):
            Scene(id="intro", duration="5")

    def test_full_scene(self):
        scene = Scene(
            id="test",
            duration="3s",
            character=Character(asset="./char.moho"),
            audio=AudioConfig(text="Hola"),
            background=Background(color="#000000"),
        )
        assert scene.id == "test"
        assert scene.character is not None
        assert scene.audio is not None


class TestAnimationSpec:
    def test_from_yaml(self):
        spec_data = {
            "version": "1.0",
            "output": {"format": "mp4", "resolution": "1920x1080", "fps": 30},
            "scenes": [
                {
                    "id": "intro",
                    "duration": "5s",
                    "audio": {"text": "Hola mundo", "voice": "alloy"},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(spec_data, f)
            temp_path = Path(f.name)

        try:
            spec = AnimationSpec.from_yaml(temp_path)
            assert spec.version == "1.0"
            assert len(spec.scenes) == 1
            assert spec.scenes[0].id == "intro"
        finally:
            temp_path.unlink()

    def test_empty_scenes_fails(self):
        with pytest.raises(ValueError):
            AnimationSpec(scenes=[])
