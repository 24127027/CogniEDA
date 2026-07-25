"""Schema contracts and validation tests for validity package."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas.enums import AuthorizationClass, ValidityEventType, ValiditySourceType
from schemas.validity import (
    ValidityPropagationCommand,
)


def test_validity_propagation_command_validation() -> None:
    src_id = UUID("00000000-0000-0000-0000-000000000001")
    auth_id = UUID("00000000-0000-0000-0000-000000000002")

    cmd = ValidityPropagationCommand(
        source_type=ValiditySourceType.EVIDENCE,
        source_id=src_id,
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        reason="Corrupted source file",
        authority_id=auth_id,
        workspace_id="ws-1",
        expected_source_state="active",
        expected_source_fingerprint="fp-1",
        idempotency_key="key-1",
    )
    assert cmd.contract_version == "validity-propagation/v1"

    req_fp = cmd.derive_request_fingerprint(
        authority_identity="user-1",
        authority_class=AuthorizationClass.USER_GOVERNED,
        authority_purpose="evaluation",
        authority_operation="invalidate",
    )
    assert isinstance(req_fp, str)
    assert len(req_fp) == 64  # sha256 hex length

    # Empty reason error
    with pytest.raises(ValidationError, match="Field cannot be empty or whitespace"):
        ValidityPropagationCommand(
            source_type=ValiditySourceType.EVIDENCE,
            source_id=src_id,
            event_type=ValidityEventType.EVIDENCE_INVALIDATION,
            reason="  ",
            authority_id=auth_id,
            workspace_id="ws-1",
            expected_source_state="active",
            expected_source_fingerprint="fp-1",
            idempotency_key="key-1",
        )
