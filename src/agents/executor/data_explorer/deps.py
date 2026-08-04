from __future__ import annotations

from collections.abc import Callable

from schemas.artifacts import DataProfile, Evidence

AdmissionCall = Callable[[Evidence | DataProfile], bool]