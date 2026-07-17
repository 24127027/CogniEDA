"""Small shared helpers for repository implementations."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, select


def schema_to_record_payload(
    schema: BaseModel,
    *,
    json_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Convert a Pydantic schema model into a record-constructor payload."""

    json_fields = json_fields or set()
    python_payload = schema.model_dump(mode="python")
    json_payload = schema.model_dump(mode="json")
    for field_name in json_fields:
        if field_name in json_payload:
            python_payload[field_name] = json_payload[field_name]
    return python_payload


def record_to_schema[SchemaModelT: BaseModel](
    schema_type: type[SchemaModelT],
    record: SQLModel,
) -> SchemaModelT:
    """Hydrate a Pydantic schema model from a SQLModel record."""

    return schema_type.model_validate(record.model_dump())


def apply_update[RecordModelT: SQLModel](
    record: RecordModelT,
    update_model: BaseModel,
    *,
    json_fields: set[str] | None = None,
) -> RecordModelT:
    """Apply an update model onto a persisted record and refresh `updated_at` if present."""

    json_fields = json_fields or set()
    python_payload = update_model.model_dump(
        mode="python",
        exclude_unset=True,
    )
    json_payload = update_model.model_dump(
        mode="json",
        exclude_unset=True,
    )
    for field_name in json_fields:
        if field_name in json_payload:
            python_payload[field_name] = json_payload[field_name]

    for field_name, field_value in python_payload.items():
        setattr(record, field_name, field_value)

    if hasattr(record, "updated_at"):
        record.updated_at = datetime.now(UTC)

    return record


def filter_records_by_related_id[RecordModelT: SQLModel](
    records: Iterable[RecordModelT],
    *,
    field_name: str,
    related_id: UUID,
) -> list[RecordModelT]:
    """Filter JSON-backed relation arrays in Python using a UUID value."""

    related_id_str = str(related_id)
    return [record for record in records if related_id_str in getattr(record, field_name, [])]


def dedupe_preserving_order[T](values: Iterable[T]) -> list[T]:
    """Return a de-duplicated list while preserving the first-seen order."""

    deduped: list[T] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def replace_link_records[LinkModelT: SQLModel](
    session: Session,
    link_model: type[LinkModelT],
    *,
    owner_field_name: str,
    owner_id: UUID,
    payloads: Iterable[dict[str, Any]],
) -> None:
    """Replace all normalized link rows for one owner with a new payload set."""

    session.exec(delete(link_model).where(getattr(link_model, owner_field_name) == owner_id))
    for payload in payloads:
        session.add(link_model(**payload))


def load_related_ids[LinkModelT: SQLModel](
    session: Session,
    link_model: type[LinkModelT],
    *,
    owner_field_name: str,
    owner_id: UUID,
    related_field_name: str,
) -> list[UUID]:
    """Load normalized related ids for one owner from an association table."""

    statement = select(link_model).where(getattr(link_model, owner_field_name) == owner_id)
    records = session.exec(statement).all()
    return [getattr(record, related_field_name) for record in records]


def load_records_by_ids[RecordModelT: SQLModel](
    session: Session,
    record_type: type[RecordModelT],
    record_ids: Iterable[UUID],
) -> list[RecordModelT]:
    """Load persisted records by primary key while preserving the requested order."""

    records: list[RecordModelT] = []
    for record_id in dedupe_preserving_order(record_ids):
        record = session.get(record_type, record_id)
        if record is not None:
            records.append(record)
    return records
