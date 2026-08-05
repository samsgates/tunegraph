from __future__ import annotations

from dataclasses import dataclass

from tunegraph.domain.enums import Role


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    organization_id: str
    roles: frozenset[Role]
    auth_type: str
