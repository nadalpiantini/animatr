"""Pytest fixtures for ANIMATR tests."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from animatr.db.manager import ProjectManager
from animatr.schema import AnimationSpec, AudioConfig, Background, Character, OutputConfig, Scene


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Directorio temporal para tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(temp_dir: Path) -> Generator[ProjectManager, None, None]:
    """Base de datos temporal para tests."""
    db_path = temp_dir / "test.db"
    manager = ProjectManager(db_path)
    yield manager


@pytest.fixture
def sample_audio_config() -> AudioConfig:
    """Configuración de audio de ejemplo."""
    return AudioConfig(
        text="Hola, bienvenido a ANIMATR.",
        voice="alloy",
        provider="openai",
        speed=1.0,
    )


@pytest.fixture
def sample_character() -> Character:
    """Personaje de ejemplo."""
    return Character(
        asset="characters/presenter.moho",
        position="center",
        expression="happy",
        scale=1.0,
    )


@pytest.fixture
def sample_background() -> Background:
    """Fondo de ejemplo."""
    return Background(color="#1E3A5F")


@pytest.fixture
def sample_scene(
    sample_audio_config: AudioConfig,
    sample_character: Character,
    sample_background: Background,
) -> Scene:
    """Escena de ejemplo."""
    return Scene(
        id="intro",
        duration="5s",
        character=sample_character,
        audio=sample_audio_config,
        background=sample_background,
    )


@pytest.fixture
def sample_output_config() -> OutputConfig:
    """Configuración de salida de ejemplo."""
    return OutputConfig(
        format="mp4",
        resolution="1920x1080",
        fps=30,
    )


@pytest.fixture
def sample_spec(sample_scene: Scene, sample_output_config: OutputConfig) -> AnimationSpec:
    """Spec de animación de ejemplo."""
    return AnimationSpec(
        version="1.0",
        output=sample_output_config,
        scenes=[sample_scene],
    )


@pytest.fixture
def sample_yaml_content() -> str:
    """Contenido YAML de ejemplo."""
    return """
version: "1.0"
output:
  format: mp4
  resolution: 1920x1080
  fps: 30
scenes:
  - id: intro
    duration: "5s"
    audio:
      text: "Bienvenido a ANIMATR"
      voice: alloy
      provider: openai
    background:
      color: "#1E3A5F"
    character:
      asset: characters/presenter.moho
      position: center
      expression: happy
  - id: main
    duration: "10s"
    audio:
      text: "Este es el contenido principal"
      voice: nova
      provider: openai
    background:
      color: "#2E4A6F"
"""


@pytest.fixture
def sample_yaml_file(temp_dir: Path, sample_yaml_content: str) -> Path:
    """Archivo YAML de ejemplo."""
    yaml_path = temp_dir / "sample.yaml"
    yaml_path.write_text(sample_yaml_content)
    return yaml_path


@pytest.fixture
def mock_audio_file(temp_dir: Path) -> Path:
    """Archivo de audio mock para tests."""
    audio_path = temp_dir / "test.mp3"
    # Crear archivo vacío para simular audio
    audio_path.write_bytes(b"\x00" * 1024)
    return audio_path


@pytest.fixture
def mock_moho_file(temp_dir: Path) -> Path:
    """Archivo Moho mock para tests."""
    moho_path = temp_dir / "character.moho"
    moho_path.write_text("<moho_project></moho_project>")
    return moho_path
