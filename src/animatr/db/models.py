"""Database models for ANIMATR projects."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class RenderStatus(Enum):
    """Estado de un trabajo de renderizado."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetType(Enum):
    """Tipo de asset."""

    CHARACTER = "character"
    BACKGROUND = "background"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    OTHER = "other"


@dataclass
class Project:
    """Representa un proyecto ANIMATR."""

    id: int | None = None
    name: str = ""
    description: str = ""
    spec_path: str | None = None
    spec_yaml: str | None = None
    output_path: str | None = None
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def spec_file(self) -> Path | None:
        """Path al archivo spec."""
        return Path(self.spec_path) if self.spec_path else None

    @property
    def output_file(self) -> Path | None:
        """Path al archivo de salida."""
        return Path(self.output_path) if self.output_path else None

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "spec_path": self.spec_path,
            "spec_yaml": self.spec_yaml,
            "output_path": self.output_path,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Asset:
    """Representa un asset del proyecto."""

    id: int | None = None
    project_id: int | None = None
    name: str = ""
    asset_type: AssetType = AssetType.OTHER
    file_path: str = ""
    file_size: int = 0
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> Path:
        """Path al archivo del asset."""
        return Path(self.file_path)

    @property
    def exists(self) -> bool:
        """Verifica si el archivo existe."""
        return self.path.exists()

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RenderJob:
    """Representa un trabajo de renderizado."""

    id: int | None = None
    project_id: int | None = None
    status: RenderStatus = RenderStatus.PENDING
    progress: float = 0.0
    current_scene: str | None = None
    total_scenes: int = 0
    completed_scenes: int = 0
    output_path: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Verifica si el job está activo."""
        return self.status in (RenderStatus.QUEUED, RenderStatus.PROCESSING)

    @property
    def is_complete(self) -> bool:
        """Verifica si el job terminó."""
        return self.status in (
            RenderStatus.COMPLETED,
            RenderStatus.FAILED,
            RenderStatus.CANCELLED,
        )

    @property
    def duration_seconds(self) -> float | None:
        """Duración del renderizado en segundos."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status.value,
            "progress": self.progress,
            "current_scene": self.current_scene,
            "total_scenes": self.total_scenes,
            "completed_scenes": self.completed_scenes,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class SceneRender:
    """Estado de renderizado de una escena individual."""

    id: int | None = None
    render_job_id: int | None = None
    scene_id: str = ""
    status: RenderStatus = RenderStatus.PENDING
    audio_path: str | None = None
    moho_path: str | None = None
    blender_path: str | None = None
    final_path: str | None = None
    duration: float = 0.0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "render_job_id": self.render_job_id,
            "scene_id": self.scene_id,
            "status": self.status.value,
            "audio_path": self.audio_path,
            "moho_path": self.moho_path,
            "blender_path": self.blender_path,
            "final_path": self.final_path,
            "duration": self.duration,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
