"""Project Manager - SQLite persistence layer for ANIMATR."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from animatr.db.models import Asset, AssetType, Project, RenderJob, RenderStatus, SceneRender

# Default database location
DEFAULT_DB_PATH = Path.home() / ".animatr" / "projects.db"


class ProjectManager:
    """Gestiona la persistencia de proyectos ANIMATR en SQLite."""

    def __init__(self, db_path: Path | str | None = None):
        """
        Inicializa el gestor de proyectos.

        Args:
            db_path: Ruta a la base de datos SQLite. Si es None, usa ubicación por defecto.
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager para conexiones a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign key support for cascade deletes
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Inicializa el esquema de la base de datos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabla de proyectos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    spec_path TEXT,
                    spec_yaml TEXT,
                    output_path TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # Tabla de assets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    duration REAL,
                    width INTEGER,
                    height INTEGER,
                    created_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Tabla de render jobs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS render_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    current_scene TEXT,
                    total_scenes INTEGER DEFAULT 0,
                    completed_scenes INTEGER DEFAULT 0,
                    output_path TEXT,
                    error_message TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Tabla de scene renders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scene_renders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    render_job_id INTEGER NOT NULL,
                    scene_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    audio_path TEXT,
                    moho_path TEXT,
                    blender_path TEXT,
                    final_path TEXT,
                    duration REAL DEFAULT 0.0,
                    error_message TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (render_job_id) REFERENCES render_jobs(id) ON DELETE CASCADE
                )
            """)

            # Índices para mejorar rendimiento
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_render_jobs_project ON render_jobs(project_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_scene_renders_job ON scene_renders(render_job_id)"
            )

    # ==========================================================================
    # Project CRUD
    # ==========================================================================

    def create_project(self, name: str, description: str = "", **kwargs: Any) -> Project:
        """
        Crea un nuevo proyecto.

        Args:
            name: Nombre del proyecto
            description: Descripción opcional
            **kwargs: Campos adicionales (spec_path, spec_yaml, etc.)

        Returns:
            Project creado con ID asignado
        """
        now = datetime.now().isoformat()
        metadata = json.dumps(kwargs.get("metadata", {}))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO projects (name, description, spec_path, spec_yaml, output_path,
                                       status, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    kwargs.get("spec_path"),
                    kwargs.get("spec_yaml"),
                    kwargs.get("output_path"),
                    kwargs.get("status", "draft"),
                    now,
                    now,
                    metadata,
                ),
            )
            project_id = cursor.lastrowid

        return self.get_project(project_id)  # type: ignore

    def get_project(self, project_id: int) -> Project | None:
        """Obtiene un proyecto por ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_project(row)

    def get_project_by_name(self, name: str) -> Project | None:
        """Obtiene un proyecto por nombre."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_project(row)

    def list_projects(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """Lista proyectos con filtros opcionales."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                    (status, limit, offset),
                )
            else:
                cursor.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )

            rows = cursor.fetchall()

        return [self._row_to_project(row) for row in rows]

    def update_project(self, project_id: int, **updates: Any) -> Project | None:
        """
        Actualiza campos de un proyecto.

        Args:
            project_id: ID del proyecto
            **updates: Campos a actualizar

        Returns:
            Project actualizado o None si no existe
        """
        project = self.get_project(project_id)
        if not project:
            return None

        updates["updated_at"] = datetime.now().isoformat()

        # Manejar metadata como JSON
        if "metadata" in updates:
            updates["metadata"] = json.dumps(updates["metadata"])

        # Construir query dinámicamente
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [project_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?",
                values,
            )

        return self.get_project(project_id)

    def delete_project(self, project_id: int) -> bool:
        """Elimina un proyecto y todos sus datos relacionados."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cursor.rowcount > 0

    def _row_to_project(self, row: sqlite3.Row) -> Project:
        """Convierte una fila de SQLite a objeto Project."""
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            spec_path=row["spec_path"],
            spec_yaml=row["spec_yaml"],
            output_path=row["output_path"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"] or "{}"),
        )

    # ==========================================================================
    # Asset CRUD
    # ==========================================================================

    def add_asset(
        self,
        project_id: int,
        name: str,
        asset_type: AssetType | str,
        file_path: str | Path,
        **kwargs: Any,
    ) -> Asset:
        """Añade un asset a un proyecto."""
        if isinstance(asset_type, str):
            asset_type = AssetType(asset_type)

        file_path = Path(file_path)
        file_size = file_path.stat().st_size if file_path.exists() else 0
        now = datetime.now().isoformat()
        metadata = json.dumps(kwargs.get("metadata", {}))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO assets (project_id, name, asset_type, file_path, file_size,
                                    duration, width, height, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name,
                    asset_type.value,
                    str(file_path),
                    file_size,
                    kwargs.get("duration"),
                    kwargs.get("width"),
                    kwargs.get("height"),
                    now,
                    metadata,
                ),
            )
            asset_id = cursor.lastrowid

        return self.get_asset(asset_id)  # type: ignore

    def get_asset(self, asset_id: int) -> Asset | None:
        """Obtiene un asset por ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_asset(row)

    def list_assets(
        self,
        project_id: int,
        asset_type: AssetType | str | None = None,
    ) -> list[Asset]:
        """Lista assets de un proyecto."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if asset_type:
                if isinstance(asset_type, AssetType):
                    asset_type = asset_type.value
                cursor.execute(
                    "SELECT * FROM assets WHERE project_id = ? AND asset_type = ? ORDER BY created_at",
                    (project_id, asset_type),
                )
            else:
                cursor.execute(
                    "SELECT * FROM assets WHERE project_id = ? ORDER BY created_at",
                    (project_id,),
                )

            rows = cursor.fetchall()

        return [self._row_to_asset(row) for row in rows]

    def delete_asset(self, asset_id: int) -> bool:
        """Elimina un asset."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            return cursor.rowcount > 0

    def _row_to_asset(self, row: sqlite3.Row) -> Asset:
        """Convierte una fila de SQLite a objeto Asset."""
        return Asset(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            asset_type=AssetType(row["asset_type"]),
            file_path=row["file_path"],
            file_size=row["file_size"],
            duration=row["duration"],
            width=row["width"],
            height=row["height"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"] or "{}"),
        )

    # ==========================================================================
    # Render Job CRUD
    # ==========================================================================

    def create_render_job(self, project_id: int, total_scenes: int = 0) -> RenderJob:
        """Crea un nuevo trabajo de renderizado."""
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO render_jobs (project_id, status, total_scenes, created_at, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, RenderStatus.PENDING.value, total_scenes, now, "{}"),
            )
            job_id = cursor.lastrowid

        return self.get_render_job(job_id)  # type: ignore

    def get_render_job(self, job_id: int) -> RenderJob | None:
        """Obtiene un render job por ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM render_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_render_job(row)

    def get_active_render_job(self, project_id: int) -> RenderJob | None:
        """Obtiene el render job activo de un proyecto."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM render_jobs
                WHERE project_id = ? AND status IN (?, ?)
                ORDER BY created_at DESC LIMIT 1
                """,
                (project_id, RenderStatus.QUEUED.value, RenderStatus.PROCESSING.value),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_render_job(row)

    def list_render_jobs(
        self,
        project_id: int | None = None,
        status: RenderStatus | None = None,
        limit: int = 50,
    ) -> list[RenderJob]:
        """Lista render jobs con filtros opcionales."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            conditions = []
            params: list[Any] = []

            if project_id is not None:
                conditions.append("project_id = ?")
                params.append(project_id)

            if status is not None:
                conditions.append("status = ?")
                params.append(status.value)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            params.append(limit)

            cursor.execute(
                f"SELECT * FROM render_jobs WHERE {where_clause} ORDER BY created_at DESC LIMIT ?",
                params,
            )
            rows = cursor.fetchall()

        return [self._row_to_render_job(row) for row in rows]

    def update_render_job(
        self,
        job_id: int,
        status: RenderStatus | None = None,
        progress: float | None = None,
        current_scene: str | None = None,
        completed_scenes: int | None = None,
        output_path: str | None = None,
        error_message: str | None = None,
        **kwargs: Any,
    ) -> RenderJob | None:
        """Actualiza un render job."""
        updates: dict[str, Any] = {}

        if status is not None:
            updates["status"] = status.value
            if status == RenderStatus.PROCESSING and "started_at" not in kwargs:
                updates["started_at"] = datetime.now().isoformat()
            elif status in (RenderStatus.COMPLETED, RenderStatus.FAILED, RenderStatus.CANCELLED):
                updates["completed_at"] = datetime.now().isoformat()

        if progress is not None:
            updates["progress"] = progress
        if current_scene is not None:
            updates["current_scene"] = current_scene
        if completed_scenes is not None:
            updates["completed_scenes"] = completed_scenes
        if output_path is not None:
            updates["output_path"] = output_path
        if error_message is not None:
            updates["error_message"] = error_message

        if "metadata" in kwargs:
            updates["metadata"] = json.dumps(kwargs["metadata"])

        if not updates:
            return self.get_render_job(job_id)

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [job_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE render_jobs SET {set_clause} WHERE id = ?",
                values,
            )

        return self.get_render_job(job_id)

    def _row_to_render_job(self, row: sqlite3.Row) -> RenderJob:
        """Convierte una fila de SQLite a objeto RenderJob."""
        return RenderJob(
            id=row["id"],
            project_id=row["project_id"],
            status=RenderStatus(row["status"]),
            progress=row["progress"],
            current_scene=row["current_scene"],
            total_scenes=row["total_scenes"],
            completed_scenes=row["completed_scenes"],
            output_path=row["output_path"],
            error_message=row["error_message"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"] or "{}"),
        )

    # ==========================================================================
    # Scene Render CRUD
    # ==========================================================================

    def add_scene_render(self, render_job_id: int, scene_id: str) -> SceneRender:
        """Añade un scene render a un job."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scene_renders (render_job_id, scene_id, status)
                VALUES (?, ?, ?)
                """,
                (render_job_id, scene_id, RenderStatus.PENDING.value),
            )
            scene_render_id = cursor.lastrowid

        return self.get_scene_render(scene_render_id)  # type: ignore

    def get_scene_render(self, scene_render_id: int) -> SceneRender | None:
        """Obtiene un scene render por ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scene_renders WHERE id = ?", (scene_render_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_scene_render(row)

    def list_scene_renders(self, render_job_id: int) -> list[SceneRender]:
        """Lista scene renders de un job."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM scene_renders WHERE render_job_id = ? ORDER BY id",
                (render_job_id,),
            )
            rows = cursor.fetchall()

        return [self._row_to_scene_render(row) for row in rows]

    def update_scene_render(
        self,
        scene_render_id: int,
        status: RenderStatus | None = None,
        audio_path: str | None = None,
        moho_path: str | None = None,
        blender_path: str | None = None,
        final_path: str | None = None,
        duration: float | None = None,
        error_message: str | None = None,
    ) -> SceneRender | None:
        """Actualiza un scene render."""
        updates: dict[str, Any] = {}

        if status is not None:
            updates["status"] = status.value
            if status == RenderStatus.PROCESSING:
                updates["started_at"] = datetime.now().isoformat()
            elif status in (RenderStatus.COMPLETED, RenderStatus.FAILED):
                updates["completed_at"] = datetime.now().isoformat()

        if audio_path is not None:
            updates["audio_path"] = audio_path
        if moho_path is not None:
            updates["moho_path"] = moho_path
        if blender_path is not None:
            updates["blender_path"] = blender_path
        if final_path is not None:
            updates["final_path"] = final_path
        if duration is not None:
            updates["duration"] = duration
        if error_message is not None:
            updates["error_message"] = error_message

        if not updates:
            return self.get_scene_render(scene_render_id)

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [scene_render_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE scene_renders SET {set_clause} WHERE id = ?",
                values,
            )

        return self.get_scene_render(scene_render_id)

    def _row_to_scene_render(self, row: sqlite3.Row) -> SceneRender:
        """Convierte una fila de SQLite a objeto SceneRender."""
        return SceneRender(
            id=row["id"],
            render_job_id=row["render_job_id"],
            scene_id=row["scene_id"],
            status=RenderStatus(row["status"]),
            audio_path=row["audio_path"],
            moho_path=row["moho_path"],
            blender_path=row["blender_path"],
            final_path=row["final_path"],
            duration=row["duration"],
            error_message=row["error_message"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def get_project_summary(self, project_id: int) -> dict[str, Any] | None:
        """Obtiene un resumen completo del proyecto."""
        project = self.get_project(project_id)
        if not project:
            return None

        assets = self.list_assets(project_id)
        jobs = self.list_render_jobs(project_id, limit=10)

        return {
            "project": project.to_dict(),
            "assets": {
                "total": len(assets),
                "by_type": {
                    t.value: len([a for a in assets if a.asset_type == t])
                    for t in AssetType
                    if any(a.asset_type == t for a in assets)
                },
            },
            "render_jobs": {
                "total": len(jobs),
                "latest": jobs[0].to_dict() if jobs else None,
                "completed": len([j for j in jobs if j.status == RenderStatus.COMPLETED]),
                "failed": len([j for j in jobs if j.status == RenderStatus.FAILED]),
            },
        }

    def vacuum(self) -> None:
        """Optimiza la base de datos."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")

    def backup(self, backup_path: Path) -> None:
        """Crea un backup de la base de datos."""
        import shutil

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, backup_path)

    def stats(self) -> dict[str, Any]:
        """Obtiene estadísticas generales."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM projects")
            total_projects = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM assets")
            total_assets = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM render_jobs")
            total_jobs = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM render_jobs WHERE status = ?",
                (RenderStatus.COMPLETED.value,),
            )
            completed_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(file_size) FROM assets")
            total_size = cursor.fetchone()[0] or 0

        return {
            "total_projects": total_projects,
            "total_assets": total_assets,
            "total_render_jobs": total_jobs,
            "completed_render_jobs": completed_jobs,
            "total_asset_size_bytes": total_size,
            "total_asset_size_mb": round(total_size / (1024 * 1024), 2),
            "database_path": str(self.db_path),
        }
