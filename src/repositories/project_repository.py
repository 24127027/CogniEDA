"""Persistence access for project artifacts."""

from __future__ import annotations

import builtins
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import ProjectRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Project
from schemas.enums import ProjectStatus

PROJECT_JSON_FIELDS = {"research_questions"}


class ProjectUpdate(BaseModel):
    """Typed mutable fields for project updates."""

    name: str | None = None
    objective: str | None = None
    research_questions: list[str] | None = None
    status: ProjectStatus | None = None
    updated_at: datetime | None = None


class ProjectRepository:
    """Artifact-specific CRUD access for projects."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, project: Project) -> Project:
        """Persist and return a new project artifact."""

        record = ProjectRecord(**schema_to_record_payload(project, json_fields=PROJECT_JSON_FIELDS))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Project, record)

    def get_by_id(self, project_id: UUID) -> Project | None:
        """Return a project by primary id if it exists."""

        record = self._session.get(ProjectRecord, project_id)
        if record is None:
            return None
        return record_to_schema(Project, record)

    def list(self, *, status: ProjectStatus | None = None) -> list[Project]:
        """List projects, optionally scoped to a status."""

        statement = select(ProjectRecord).order_by(desc(ProjectRecord.updated_at))
        if status is not None:
            statement = statement.where(ProjectRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Project, record) for record in records]

    def list_active(self) -> builtins.list[Project]:
        """List only active projects."""

        return self.list(status=ProjectStatus.ACTIVE)

    def update(self, project_id: UUID, update: ProjectUpdate) -> Project | None:
        """Apply a typed partial update to a project record."""

        record = self._session.get(ProjectRecord, project_id)
        if record is None:
            return None
        apply_update(record, update, json_fields=PROJECT_JSON_FIELDS)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Project, record)
