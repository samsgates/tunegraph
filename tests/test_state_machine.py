import pytest

from tunegraph.domain.enums import PatchState
from tunegraph.domain.state_machine import ensure_patch_transition


def test_valid_patch_transition() -> None:
    ensure_patch_transition(PatchState.DRAFT, PatchState.TRAINING)


def test_invalid_patch_transition() -> None:
    with pytest.raises(ValueError):
        ensure_patch_transition(PatchState.DRAFT, PatchState.PRODUCTION)
