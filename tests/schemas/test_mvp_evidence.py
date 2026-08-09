"""M1-A direct Task-to-Evidence contract."""

import json
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from cognieda.schemas import Evidence, EvidenceProvenance


def _provenance(data_profile_id):
    return EvidenceProvenance(
        producer_role="data_explorer",
        work_reference="de:run-001",
        dataset_reference="dataset:customers.csv",
        data_profile_id=data_profile_id,
        tool_reference="pandas:groupby",
        code_reference="analysis/customer_segments.py",
    )


def test_evidence_links_real_task_and_data_profile_without_scientific_refs() -> None:
    task_id = uuid4()
    data_profile_id = uuid4()
    evidence = Evidence(
        task_id=task_id,
        data_profile_id=data_profile_id,
        content={"segment": "premium", "count": 124, "rate": 0.37},
        provenance=_provenance(data_profile_id),
        artifact_refs=("artifacts/segment-counts.json",),
    )

    assert evidence.task_id == task_id
    assert evidence.data_profile_id == data_profile_id
    assert evidence.content == {"segment": "premium", "count": 124, "rate": 0.37}
    assert not {"hypothesis_id", "analysis_frame_ref", "execution_run_ref"} & set(
        Evidence.model_fields
    )
    json.dumps(evidence.model_dump(mode="json"), allow_nan=False)


def test_evidence_is_immutable() -> None:
    data_profile_id = uuid4()
    evidence = Evidence(
        task_id=uuid4(),
        data_profile_id=data_profile_id,
        content={"row_count": 3, "groups": [{"name": "premium"}]},
        provenance=_provenance(data_profile_id),
    )

    with pytest.raises(ValidationError):
        evidence.task_id = uuid4()
    with pytest.raises(TypeError, match="immutable"):
        evidence.content["row_count"] = 4
    with pytest.raises(TypeError):
        evidence.content["groups"][0]["name"] = "changed"


def test_evidence_rejects_mismatched_provenance_profile() -> None:
    with pytest.raises(ValidationError, match="same DataProfile"):
        Evidence(
            task_id=uuid4(),
            data_profile_id=uuid4(),
            content={"row_count": 3},
            provenance=_provenance(uuid4()),
        )


@pytest.mark.parametrize(
    "unsupported",
    [
        pd.DataFrame({"value": [1]}),
        pd.Series([1]),
        np.int64(1),
        object(),
        float("nan"),
    ],
)
def test_evidence_rejects_live_or_non_json_runtime_objects(unsupported) -> None:
    data_profile_id = uuid4()
    with pytest.raises(ValidationError, match="content"):
        Evidence(
            task_id=uuid4(),
            data_profile_id=data_profile_id,
            content={"result": unsupported},
            provenance=_provenance(data_profile_id),
        )


def test_evidence_rejects_non_string_object_keys() -> None:
    data_profile_id = uuid4()
    with pytest.raises(ValidationError, match="string object keys"):
        Evidence(
            task_id=uuid4(),
            data_profile_id=data_profile_id,
            content={1: "value"},
            provenance=_provenance(data_profile_id),
        )
