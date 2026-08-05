from __future__ import annotations

from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tunegraph.config import Settings
from tunegraph.db.models import PatchConflict, PatchDependency, PatchRelease
from tunegraph.domain.enums import PatchState
from tunegraph.schemas import GraphValidationResult
from tunegraph.services.integrity import patch_integrity_errors

ALLOWED_GRAPH_STATES = {
    PatchState.APPROVED,
    PatchState.STAGED,
    PatchState.CANARY,
    PatchState.PRODUCTION,
    PatchState.DEPRECATED,
}


class GraphResolver:
    async def validate(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        base_model_id: str,
        patch_ids: list[str],
        settings: Settings | None = None,
    ) -> GraphValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        selected: dict[str, PatchRelease] = {}

        rows = (
            await session.execute(
                select(PatchRelease).where(
                    PatchRelease.organization_id == organization_id,
                    PatchRelease.id.in_(patch_ids),
                )
            )
        ).scalars().all()
        selected.update({row.id: row for row in rows})
        missing = sorted(set(patch_ids) - set(selected))
        if missing:
            errors.append(f"Unknown patch IDs: {missing}")

        queue = deque(selected)
        while queue:
            patch_id = queue.popleft()
            dependencies = (
                await session.execute(
                    select(PatchDependency).where(PatchDependency.patch_id == patch_id)
                )
            ).scalars().all()
            for dependency in dependencies:
                if not dependency.required:
                    continue
                required = await session.get(PatchRelease, dependency.required_patch_id)
                if required is None or required.organization_id != organization_id:
                    errors.append(
                        f"Patch {patch_id} requires missing patch {dependency.required_patch_id}"
                    )
                    continue
                if required.id not in selected:
                    selected[required.id] = required
                    queue.append(required.id)

        for patch in selected.values():
            if patch.base_model_id != base_model_id:
                errors.append(
                    f"Patch {patch.id} targets base model {patch.base_model_id}, expected {base_model_id}"
                )
            if PatchState(patch.state) not in ALLOWED_GRAPH_STATES:
                errors.append(f"Patch {patch.id} is not deployable in state {patch.state}")
            if patch.state == PatchState.DEPRECATED:
                warnings.append(f"Patch {patch.id} is deprecated")
            if settings is not None:
                errors.extend(
                    f"Patch {patch.id}: {error}"
                    for error in patch_integrity_errors(patch, settings)
                )

        conflicts = (
            await session.execute(
                select(PatchConflict).where(PatchConflict.patch_id.in_(list(selected)))
            )
        ).scalars().all()
        for conflict in conflicts:
            if conflict.conflicting_patch_id in selected:
                message = (
                    f"Patch {conflict.patch_id} conflicts with {conflict.conflicting_patch_id}: "
                    f"{conflict.reason}"
                )
                if conflict.severity == "blocking":
                    errors.append(message)
                else:
                    warnings.append(message)

        cycle = await self._find_cycle(session, list(selected))
        if cycle:
            errors.append(f"Dependency cycle detected: {' -> '.join(cycle)}")

        return GraphValidationResult(
            valid=not errors,
            resolved_patch_ids=sorted(selected),
            errors=sorted(set(errors)),
            warnings=sorted(set(warnings)),
        )

    async def _find_cycle(self, session: AsyncSession, patch_ids: list[str]) -> list[str]:
        dependencies = (
            await session.execute(
                select(PatchDependency).where(PatchDependency.patch_id.in_(patch_ids))
            )
        ).scalars().all()
        graph: dict[str, list[str]] = defaultdict(list)
        for dependency in dependencies:
            if dependency.required_patch_id in patch_ids:
                graph[dependency.patch_id].append(dependency.required_patch_id)

        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []

        def dfs(node: str) -> list[str]:
            if node in visiting:
                start = stack.index(node)
                return [*stack[start:], node]
            if node in visited:
                return []
            visiting.add(node)
            stack.append(node)
            for child in graph[node]:
                found = dfs(child)
                if found:
                    return found
            stack.pop()
            visiting.remove(node)
            visited.add(node)
            return []

        for patch_id in patch_ids:
            found = dfs(patch_id)
            if found:
                return found
        return []
