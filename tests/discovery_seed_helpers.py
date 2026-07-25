"""Test-only persistence helpers for pre-existing Discovery fixtures.

These helpers deliberately bypass Package 5 admission only when a test needs
historical graph state as input. Tests of Discovery creation must use
``AtomicDiscoveryAdmissionService`` instead.
"""

from __future__ import annotations

from sqlmodel import Session

from db.models import DiscoveryRecord
from repositories.common import record_to_schema, schema_to_record_payload
from repositories.discovery import DISCOVERY_JSON_FIELDS
from schemas.artifacts import Discovery


def seed_historical_discovery(session: Session, discovery: Discovery) -> Discovery:
    """Persist a test-only historical Discovery fixture."""

    record = DiscoveryRecord(
        **schema_to_record_payload(discovery, json_fields=DISCOVERY_JSON_FIELDS)
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record_to_schema(Discovery, record)
