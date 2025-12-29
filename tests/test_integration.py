"""Tests de integración para ANIMATR."""

from pathlib import Path

import pytest

from animatr.db.manager import ProjectManager
from animatr.db.models import AssetType, RenderStatus
from animatr.schema import AnimationSpec, AudioConfig, Background, Character, Scene


class TestFullWorkflow:
    """Tests para el flujo completo de ANIMATR."""

    def test_create_project_from_spec(
        self, temp_db: ProjectManager, sample_spec: AnimationSpec, temp_dir: Path
    ) -> None:
        """Verifica creación de proyecto desde spec."""
        # Save spec to file
        spec_path = temp_dir / "project.yaml"
        sample_spec.to_yaml(spec_path)

        # Create project
        project = temp_db.create_project(
            name="Test Animation",
            description="Created from spec",
            spec_path=str(spec_path),
            spec_yaml=spec_path.read_text(),
        )

        assert project.id is not None
        assert project.spec_path == str(spec_path)
        assert project.spec_yaml is not None

    def test_project_with_assets(
        self, temp_db: ProjectManager, temp_dir: Path
    ) -> None:
        """Verifica proyecto con múltiples assets."""
        project = temp_db.create_project(name="Multi-Asset Project")

        # Add various assets
        assets_data = [
            ("Main Character", AssetType.CHARACTER, "character.moho"),
            ("Office Background", AssetType.BACKGROUND, "office.png"),
            ("Intro Narration", AssetType.AUDIO, "intro.mp3"),
        ]

        for name, atype, filename in assets_data:
            asset_file = temp_dir / filename
            asset_file.write_bytes(b"\x00" * 100)
            temp_db.add_asset(
                project_id=project.id,
                name=name,
                asset_type=atype,
                file_path=asset_file,
            )

        assets = temp_db.list_assets(project.id)
        assert len(assets) == 3

        # Verify by type
        characters = temp_db.list_assets(project.id, asset_type=AssetType.CHARACTER)
        assert len(characters) == 1
        assert characters[0].name == "Main Character"

    def test_render_workflow(self, temp_db: ProjectManager) -> None:
        """Verifica flujo completo de renderizado."""
        # Create project
        project = temp_db.create_project(name="Render Test")

        # Create render job
        job = temp_db.create_render_job(project.id, total_scenes=3)
        assert job.status == RenderStatus.PENDING

        # Add scene renders
        scenes = ["intro", "main", "outro"]
        for scene_id in scenes:
            temp_db.add_scene_render(job.id, scene_id=scene_id)

        # Start processing
        job = temp_db.update_render_job(job.id, status=RenderStatus.PROCESSING)
        assert job.status == RenderStatus.PROCESSING
        assert job.started_at is not None

        # Process scenes
        scene_renders = temp_db.list_scene_renders(job.id)
        for i, scene in enumerate(scene_renders):
            temp_db.update_scene_render(
                scene.id,
                status=RenderStatus.COMPLETED,
                duration=5.0,
            )
            temp_db.update_render_job(
                job.id,
                completed_scenes=i + 1,
                progress=(i + 1) / len(scene_renders),
            )

        # Complete job
        job = temp_db.update_render_job(
            job.id,
            status=RenderStatus.COMPLETED,
            output_path="/output/final.mp4",
        )

        assert job.status == RenderStatus.COMPLETED
        assert job.completed_at is not None
        assert job.completed_scenes == 3
        assert job.progress == 1.0

    def test_failed_render_recovery(self, temp_db: ProjectManager) -> None:
        """Verifica recuperación de renderizado fallido."""
        project = temp_db.create_project(name="Recovery Test")

        # First attempt - fails
        job1 = temp_db.create_render_job(project.id, total_scenes=2)
        temp_db.update_render_job(job1.id, status=RenderStatus.PROCESSING)
        temp_db.update_render_job(
            job1.id,
            status=RenderStatus.FAILED,
            error_message="FFmpeg crashed",
        )

        # Second attempt - succeeds
        job2 = temp_db.create_render_job(project.id, total_scenes=2)
        temp_db.update_render_job(job2.id, status=RenderStatus.PROCESSING)
        temp_db.update_render_job(
            job2.id,
            status=RenderStatus.COMPLETED,
            output_path="/output/final.mp4",
        )

        # Verify history
        jobs = temp_db.list_render_jobs(project_id=project.id)
        assert len(jobs) == 2

        # Most recent should be completed
        assert jobs[0].status == RenderStatus.COMPLETED
        assert jobs[1].status == RenderStatus.FAILED


class TestSpecValidation:
    """Tests de validación de specs."""

    def test_minimal_valid_spec(self) -> None:
        """Verifica spec mínimo válido."""
        spec = AnimationSpec(
            scenes=[Scene(id="test", duration="5s")]
        )

        assert spec.version == "1.0"
        assert len(spec.scenes) == 1

    def test_complete_spec(self) -> None:
        """Verifica spec completo."""
        scenes = [
            Scene(
                id="intro",
                duration="5s",
                audio=AudioConfig(
                    text="Welcome to our video",
                    voice="nova",
                    provider="openai",
                ),
                background=Background(color="#1E3A5F"),
                character=Character(
                    asset="presenter.moho",
                    position="center",
                    expression="happy",
                ),
            ),
            Scene(
                id="main",
                duration="30s",
                audio=AudioConfig(
                    text="This is the main content of our video",
                    voice="nova",
                    provider="openai",
                ),
                background=Background(color="#2E4A6F"),
                character=Character(
                    asset="presenter.moho",
                    position="left",
                    expression="neutral",
                ),
            ),
            Scene(
                id="outro",
                duration="5s",
                audio=AudioConfig(
                    text="Thank you for watching",
                    voice="nova",
                    provider="openai",
                ),
                background=Background(color="#1E3A5F"),
            ),
        ]

        spec = AnimationSpec(scenes=scenes)

        assert len(spec.scenes) == 3
        total_duration = sum(s.duration_seconds for s in spec.scenes)
        assert total_duration == 40.0

    def test_spec_roundtrip(self, temp_dir: Path) -> None:
        """Verifica que spec se puede guardar y cargar."""
        original = AnimationSpec(
            scenes=[
                Scene(
                    id="test",
                    duration="10s",
                    audio=AudioConfig(text="Hello"),
                    background=Background(color="#000000"),
                )
            ]
        )

        path = temp_dir / "spec.yaml"
        original.to_yaml(path)

        loaded = AnimationSpec.from_yaml(path)

        assert loaded.version == original.version
        assert len(loaded.scenes) == len(original.scenes)
        assert loaded.scenes[0].id == original.scenes[0].id
        assert loaded.scenes[0].duration == original.scenes[0].duration


class TestMultiProjectManagement:
    """Tests para gestión de múltiples proyectos."""

    def test_list_projects_pagination(self, temp_db: ProjectManager) -> None:
        """Verifica paginación de proyectos."""
        # Create 15 projects
        for i in range(15):
            temp_db.create_project(name=f"Project {i:02d}")

        # Get first page
        page1 = temp_db.list_projects(limit=10, offset=0)
        assert len(page1) == 10

        # Get second page
        page2 = temp_db.list_projects(limit=10, offset=10)
        assert len(page2) == 5

    def test_concurrent_render_jobs(self, temp_db: ProjectManager) -> None:
        """Verifica múltiples jobs de render simultáneos."""
        projects = [
            temp_db.create_project(name=f"Project {i}")
            for i in range(3)
        ]

        # Start render for each project
        jobs = [
            temp_db.create_render_job(p.id, total_scenes=2)
            for p in projects
        ]

        # Process all simultaneously
        for job in jobs:
            temp_db.update_render_job(job.id, status=RenderStatus.PROCESSING)

        # Verify all are processing
        for project in projects:
            active = temp_db.get_active_render_job(project.id)
            assert active is not None
            assert active.status == RenderStatus.PROCESSING


class TestDataIntegrity:
    """Tests de integridad de datos."""

    def test_project_metadata_persistence(self, temp_db: ProjectManager) -> None:
        """Verifica persistencia de metadata."""
        project = temp_db.create_project(
            name="Metadata Test",
            metadata={
                "author": "Test User",
                "tags": ["test", "demo"],
                "settings": {"quality": "high"},
            },
        )

        loaded = temp_db.get_project(project.id)
        assert loaded is not None
        assert loaded.metadata["author"] == "Test User"
        assert "test" in loaded.metadata["tags"]
        assert loaded.metadata["settings"]["quality"] == "high"

    def test_asset_file_size_tracking(
        self, temp_db: ProjectManager, temp_dir: Path
    ) -> None:
        """Verifica tracking de tamaño de archivos."""
        project = temp_db.create_project(name="Size Test")

        # Create files of known sizes
        sizes = [1024, 2048, 4096]
        total_expected = sum(sizes)

        for i, size in enumerate(sizes):
            file = temp_dir / f"file_{i}.bin"
            file.write_bytes(b"\x00" * size)
            temp_db.add_asset(
                project_id=project.id,
                name=f"File {i}",
                asset_type=AssetType.OTHER,
                file_path=file,
            )

        stats = temp_db.stats()
        assert stats["total_asset_size_bytes"] == total_expected

    def test_render_duration_calculation(self, temp_db: ProjectManager) -> None:
        """Verifica cálculo de duración de render."""
        project = temp_db.create_project(name="Duration Test")
        job = temp_db.create_render_job(project.id)

        # Start processing
        temp_db.update_render_job(job.id, status=RenderStatus.PROCESSING)

        # Small delay would be needed for real duration
        # For test, just verify the fields are set correctly
        temp_db.update_render_job(job.id, status=RenderStatus.COMPLETED)

        completed = temp_db.get_render_job(job.id)
        assert completed.started_at is not None
        assert completed.completed_at is not None
        assert completed.duration_seconds is not None
