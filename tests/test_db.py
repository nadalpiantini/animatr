"""Tests para el módulo de base de datos."""

from datetime import datetime
from pathlib import Path

import pytest

from animatr.db.manager import ProjectManager
from animatr.db.models import Asset, AssetType, Project, RenderJob, RenderStatus


class TestProjectManager:
    """Tests para ProjectManager."""

    def test_init_creates_database(self, temp_dir: Path) -> None:
        """Verifica que inicialización crea la base de datos."""
        db_path = temp_dir / "test.db"
        manager = ProjectManager(db_path)

        assert db_path.exists()
        assert manager.db_path == db_path

    def test_init_creates_tables(self, temp_db: ProjectManager) -> None:
        """Verifica que se crean las tablas necesarias."""
        stats = temp_db.stats()
        assert "total_projects" in stats
        assert "total_assets" in stats
        assert "total_render_jobs" in stats


class TestProjectCRUD:
    """Tests para operaciones CRUD de proyectos."""

    def test_create_project(self, temp_db: ProjectManager) -> None:
        """Verifica creación de proyecto."""
        project = temp_db.create_project(
            name="Test Project",
            description="A test project",
        )

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.status == "draft"

    def test_get_project(self, temp_db: ProjectManager) -> None:
        """Verifica obtención de proyecto por ID."""
        created = temp_db.create_project(name="Test")
        retrieved = temp_db.get_project(created.id)  # type: ignore

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_get_nonexistent_project(self, temp_db: ProjectManager) -> None:
        """Verifica que proyecto inexistente retorna None."""
        project = temp_db.get_project(9999)
        assert project is None

    def test_get_project_by_name(self, temp_db: ProjectManager) -> None:
        """Verifica búsqueda por nombre."""
        temp_db.create_project(name="Unique Name")
        project = temp_db.get_project_by_name("Unique Name")

        assert project is not None
        assert project.name == "Unique Name"

    def test_list_projects(self, temp_db: ProjectManager) -> None:
        """Verifica listado de proyectos."""
        temp_db.create_project(name="Project 1")
        temp_db.create_project(name="Project 2")
        temp_db.create_project(name="Project 3")

        projects = temp_db.list_projects()
        assert len(projects) == 3

    def test_list_projects_with_status_filter(self, temp_db: ProjectManager) -> None:
        """Verifica filtrado por estado."""
        temp_db.create_project(name="Draft", status="draft")
        temp_db.create_project(name="Rendering", status="rendering")
        temp_db.create_project(name="Complete", status="complete")

        drafts = temp_db.list_projects(status="draft")
        assert len(drafts) == 1
        assert drafts[0].name == "Draft"

    def test_update_project(self, temp_db: ProjectManager) -> None:
        """Verifica actualización de proyecto."""
        project = temp_db.create_project(name="Original")
        updated = temp_db.update_project(
            project.id,  # type: ignore
            name="Updated",
            status="rendering",
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.status == "rendering"

    def test_delete_project(self, temp_db: ProjectManager) -> None:
        """Verifica eliminación de proyecto."""
        project = temp_db.create_project(name="To Delete")
        result = temp_db.delete_project(project.id)  # type: ignore

        assert result is True
        assert temp_db.get_project(project.id) is None  # type: ignore

    def test_delete_nonexistent_project(self, temp_db: ProjectManager) -> None:
        """Verifica que eliminar proyecto inexistente retorna False."""
        result = temp_db.delete_project(9999)
        assert result is False


class TestAssetCRUD:
    """Tests para operaciones de assets."""

    def test_add_asset(self, temp_db: ProjectManager, temp_dir: Path) -> None:
        """Verifica añadir asset a proyecto."""
        project = temp_db.create_project(name="Test")

        # Crear archivo temporal
        asset_file = temp_dir / "character.moho"
        asset_file.write_text("<moho/>")

        asset = temp_db.add_asset(
            project_id=project.id,  # type: ignore
            name="Main Character",
            asset_type=AssetType.CHARACTER,
            file_path=asset_file,
        )

        assert asset.id is not None
        assert asset.name == "Main Character"
        assert asset.asset_type == AssetType.CHARACTER
        assert asset.file_size > 0

    def test_list_assets(self, temp_db: ProjectManager, temp_dir: Path) -> None:
        """Verifica listado de assets."""
        project = temp_db.create_project(name="Test")

        for i, atype in enumerate([AssetType.CHARACTER, AssetType.BACKGROUND, AssetType.AUDIO]):
            file = temp_dir / f"asset_{i}.txt"
            file.write_text("test")
            temp_db.add_asset(
                project_id=project.id,  # type: ignore
                name=f"Asset {i}",
                asset_type=atype,
                file_path=file,
            )

        assets = temp_db.list_assets(project.id)  # type: ignore
        assert len(assets) == 3

    def test_list_assets_by_type(self, temp_db: ProjectManager, temp_dir: Path) -> None:
        """Verifica filtrado de assets por tipo."""
        project = temp_db.create_project(name="Test")

        for i in range(3):
            file = temp_dir / f"char_{i}.txt"
            file.write_text("test")
            temp_db.add_asset(
                project_id=project.id,  # type: ignore
                name=f"Character {i}",
                asset_type=AssetType.CHARACTER,
                file_path=file,
            )

        bg_file = temp_dir / "bg.txt"
        bg_file.write_text("test")
        temp_db.add_asset(
            project_id=project.id,  # type: ignore
            name="Background",
            asset_type=AssetType.BACKGROUND,
            file_path=bg_file,
        )

        characters = temp_db.list_assets(project.id, asset_type=AssetType.CHARACTER)  # type: ignore
        assert len(characters) == 3

    def test_delete_asset(self, temp_db: ProjectManager, temp_dir: Path) -> None:
        """Verifica eliminación de asset."""
        project = temp_db.create_project(name="Test")
        file = temp_dir / "test.txt"
        file.write_text("test")

        asset = temp_db.add_asset(
            project_id=project.id,  # type: ignore
            name="To Delete",
            asset_type=AssetType.OTHER,
            file_path=file,
        )

        result = temp_db.delete_asset(asset.id)  # type: ignore
        assert result is True
        assert temp_db.get_asset(asset.id) is None  # type: ignore


class TestRenderJobCRUD:
    """Tests para operaciones de render jobs."""

    def test_create_render_job(self, temp_db: ProjectManager) -> None:
        """Verifica creación de render job."""
        project = temp_db.create_project(name="Test")
        job = temp_db.create_render_job(project.id, total_scenes=5)  # type: ignore

        assert job.id is not None
        assert job.project_id == project.id
        assert job.status == RenderStatus.PENDING
        assert job.total_scenes == 5
        assert job.progress == 0.0

    def test_update_render_job_status(self, temp_db: ProjectManager) -> None:
        """Verifica actualización de estado de job."""
        project = temp_db.create_project(name="Test")
        job = temp_db.create_render_job(project.id)  # type: ignore

        updated = temp_db.update_render_job(
            job.id,  # type: ignore
            status=RenderStatus.PROCESSING,
            progress=0.25,
            current_scene="scene_1",
        )

        assert updated is not None
        assert updated.status == RenderStatus.PROCESSING
        assert updated.progress == 0.25
        assert updated.current_scene == "scene_1"
        assert updated.started_at is not None

    def test_complete_render_job(self, temp_db: ProjectManager) -> None:
        """Verifica completar un job."""
        project = temp_db.create_project(name="Test")
        job = temp_db.create_render_job(project.id, total_scenes=2)  # type: ignore

        # Start processing
        temp_db.update_render_job(job.id, status=RenderStatus.PROCESSING)  # type: ignore

        # Complete
        updated = temp_db.update_render_job(
            job.id,  # type: ignore
            status=RenderStatus.COMPLETED,
            progress=1.0,
            completed_scenes=2,
            output_path="/output/final.mp4",
        )

        assert updated is not None
        assert updated.status == RenderStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.output_path == "/output/final.mp4"

    def test_fail_render_job(self, temp_db: ProjectManager) -> None:
        """Verifica fallar un job."""
        project = temp_db.create_project(name="Test")
        job = temp_db.create_render_job(project.id)  # type: ignore

        updated = temp_db.update_render_job(
            job.id,  # type: ignore
            status=RenderStatus.FAILED,
            error_message="FFmpeg failed with exit code 1",
        )

        assert updated is not None
        assert updated.status == RenderStatus.FAILED
        assert updated.error_message == "FFmpeg failed with exit code 1"

    def test_get_active_render_job(self, temp_db: ProjectManager) -> None:
        """Verifica obtener job activo."""
        project = temp_db.create_project(name="Test")

        # No active jobs initially
        assert temp_db.get_active_render_job(project.id) is None  # type: ignore

        # Create and start job
        job = temp_db.create_render_job(project.id)  # type: ignore
        temp_db.update_render_job(job.id, status=RenderStatus.PROCESSING)  # type: ignore

        active = temp_db.get_active_render_job(project.id)  # type: ignore
        assert active is not None
        assert active.id == job.id

    def test_list_render_jobs(self, temp_db: ProjectManager) -> None:
        """Verifica listado de render jobs."""
        project = temp_db.create_project(name="Test")

        for _ in range(3):
            temp_db.create_render_job(project.id)  # type: ignore

        jobs = temp_db.list_render_jobs(project_id=project.id)  # type: ignore
        assert len(jobs) == 3


class TestSceneRender:
    """Tests para scene renders."""

    def test_add_scene_render(self, temp_db: ProjectManager) -> None:
        """Verifica añadir scene render."""
        project = temp_db.create_project(name="Test")
        job = temp_db.create_render_job(project.id)  # type: ignore

        scene_render = temp_db.add_scene_render(job.id, scene_id="intro")  # type: ignore

        assert scene_render.id is not None
        assert scene_render.scene_id == "intro"
        assert scene_render.status == RenderStatus.PENDING

    def test_update_scene_render(self, temp_db: ProjectManager) -> None:
        """Verifica actualización de scene render."""
        project = temp_db.create_project(name="Test")
        job = temp_db.create_render_job(project.id)  # type: ignore
        scene = temp_db.add_scene_render(job.id, scene_id="intro")  # type: ignore

        updated = temp_db.update_scene_render(
            scene.id,  # type: ignore
            status=RenderStatus.COMPLETED,
            audio_path="/audio/intro.mp3",
            moho_path="/moho/intro.mov",
            blender_path="/blender/intro.mp4",
            final_path="/final/intro.mp4",
            duration=5.5,
        )

        assert updated is not None
        assert updated.status == RenderStatus.COMPLETED
        assert updated.audio_path == "/audio/intro.mp3"
        assert updated.duration == 5.5

    def test_list_scene_renders(self, temp_db: ProjectManager) -> None:
        """Verifica listado de scene renders."""
        project = temp_db.create_project(name="Test")
        job = temp_db.create_render_job(project.id)  # type: ignore

        for scene_id in ["intro", "main", "outro"]:
            temp_db.add_scene_render(job.id, scene_id=scene_id)  # type: ignore

        renders = temp_db.list_scene_renders(job.id)  # type: ignore
        assert len(renders) == 3


class TestProjectSummary:
    """Tests para resumen de proyecto."""

    def test_get_project_summary(self, temp_db: ProjectManager, temp_dir: Path) -> None:
        """Verifica obtención de resumen."""
        project = temp_db.create_project(name="Test", description="Test project")

        # Add assets
        for i in range(2):
            file = temp_dir / f"char_{i}.txt"
            file.write_text("test")
            temp_db.add_asset(
                project_id=project.id,  # type: ignore
                name=f"Character {i}",
                asset_type=AssetType.CHARACTER,
                file_path=file,
            )

        # Add render job
        job = temp_db.create_render_job(project.id, total_scenes=3)  # type: ignore
        temp_db.update_render_job(job.id, status=RenderStatus.COMPLETED)  # type: ignore

        summary = temp_db.get_project_summary(project.id)  # type: ignore

        assert summary is not None
        assert summary["project"]["name"] == "Test"
        assert summary["assets"]["total"] == 2
        assert summary["render_jobs"]["total"] == 1
        assert summary["render_jobs"]["completed"] == 1


class TestDatabaseUtilities:
    """Tests para utilidades de base de datos."""

    def test_stats(self, temp_db: ProjectManager) -> None:
        """Verifica estadísticas."""
        stats = temp_db.stats()

        assert "total_projects" in stats
        assert "total_assets" in stats
        assert "total_render_jobs" in stats
        assert "database_path" in stats

    def test_backup(self, temp_db: ProjectManager, temp_dir: Path) -> None:
        """Verifica backup de base de datos."""
        temp_db.create_project(name="Test")

        backup_path = temp_dir / "backup.db"
        temp_db.backup(backup_path)

        assert backup_path.exists()

        # Verify backup is valid
        backup_manager = ProjectManager(backup_path)
        projects = backup_manager.list_projects()
        assert len(projects) == 1

    def test_vacuum(self, temp_db: ProjectManager) -> None:
        """Verifica que vacuum no falla."""
        temp_db.create_project(name="Test")
        temp_db.vacuum()  # Should not raise


class TestCascadeDelete:
    """Tests para eliminación en cascada."""

    def test_delete_project_cascades_to_assets(
        self, temp_db: ProjectManager, temp_dir: Path
    ) -> None:
        """Verifica que eliminar proyecto elimina assets."""
        project = temp_db.create_project(name="Test")

        file = temp_dir / "test.txt"
        file.write_text("test")
        temp_db.add_asset(
            project_id=project.id,  # type: ignore
            name="Test Asset",
            asset_type=AssetType.OTHER,
            file_path=file,
        )

        temp_db.delete_project(project.id)  # type: ignore

        # Assets should be gone
        assets = temp_db.list_assets(project.id)  # type: ignore
        assert len(assets) == 0

    def test_delete_project_cascades_to_render_jobs(
        self, temp_db: ProjectManager
    ) -> None:
        """Verifica que eliminar proyecto elimina render jobs."""
        project = temp_db.create_project(name="Test")
        temp_db.create_render_job(project.id)  # type: ignore

        temp_db.delete_project(project.id)  # type: ignore

        # Jobs should be gone
        jobs = temp_db.list_render_jobs(project_id=project.id)  # type: ignore
        assert len(jobs) == 0
