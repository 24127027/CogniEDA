from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from repositories import AssumptionRepository, ProjectRepository
from schemas.artifacts import Assumption, Project
from schemas.enums import ConfidenceLevel


def test_sqlite_foreign_keys_are_enforced(db_session) -> None:
    project = ProjectRepository(db_session).create(
        Project(
            name="FK test",
            objective="Validate SQLite foreign key enforcement.",
        )
    )

    repository = AssumptionRepository(db_session)

    with pytest.raises(IntegrityError):
        repository.create(
            Assumption(
                project_id=project.project_id,
                statement="Assumption with invalid dataset reference.",
                basis="Should fail on foreign key enforcement.",
                confidence=ConfidenceLevel.LOW,
                dataset_id=uuid4(),
            )
        )
