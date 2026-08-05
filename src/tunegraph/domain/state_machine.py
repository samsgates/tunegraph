from __future__ import annotations

from tunegraph.domain.enums import PatchState

PATCH_TRANSITIONS: dict[PatchState, set[PatchState]] = {
    PatchState.DRAFT: {PatchState.TRAINING, PatchState.REVOKED},
    PatchState.TRAINING: {
        PatchState.EVALUATION_PENDING,
        PatchState.FAILED,
        PatchState.REVOKED,
    },
    PatchState.EVALUATION_PENDING: {
        PatchState.CANDIDATE,
        PatchState.FAILED,
        PatchState.REVOKED,
    },
    PatchState.FAILED: {PatchState.TRAINING, PatchState.RETIRED, PatchState.REVOKED},
    PatchState.CANDIDATE: {PatchState.REVIEW_PENDING, PatchState.FAILED, PatchState.REVOKED},
    PatchState.REVIEW_PENDING: {PatchState.APPROVED, PatchState.FAILED, PatchState.REVOKED},
    PatchState.APPROVED: {PatchState.STAGED, PatchState.DEPRECATED, PatchState.REVOKED},
    PatchState.STAGED: {PatchState.CANARY, PatchState.APPROVED, PatchState.REVOKED},
    PatchState.CANARY: {PatchState.PRODUCTION, PatchState.STAGED, PatchState.REVOKED},
    PatchState.PRODUCTION: {PatchState.DEPRECATED, PatchState.STAGED, PatchState.REVOKED},
    PatchState.DEPRECATED: {PatchState.RETIRED, PatchState.PRODUCTION, PatchState.REVOKED},
    PatchState.RETIRED: set(),
    PatchState.REVOKED: set(),
}


def ensure_patch_transition(current: PatchState, target: PatchState) -> None:
    if target not in PATCH_TRANSITIONS[current]:
        raise ValueError(f"Invalid patch state transition: {current} -> {target}")
