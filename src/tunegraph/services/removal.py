from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tunegraph.db.models import DatasetRecord, GraphRelease, PatchRelease, TrainingJob


class RemovalService:
    async def impact_report(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        target_type: str,
        target_id: str,
    ) -> dict[str, object]:
        dataset_ids: set[str] = set()
        training_job_ids: set[str] = set()
        patch_ids: set[str] = set()
        graph_ids: set[str] = set()

        if target_type == "dataset":
            dataset = await session.get(DatasetRecord, target_id)
            if dataset and dataset.organization_id == organization_id:
                dataset_ids.add(dataset.id)
        elif target_type == "patch":
            patch = await session.get(PatchRelease, target_id)
            if patch and patch.organization_id == organization_id:
                patch_ids.add(patch.id)
        else:
            datasets = (
                await session.execute(
                    select(DatasetRecord).where(
                        DatasetRecord.organization_id == organization_id,
                        DatasetRecord.source_uri.contains(target_id),
                    )
                )
            ).scalars().all()
            dataset_ids.update(dataset.id for dataset in datasets)

        if dataset_ids:
            jobs = (
                await session.execute(
                    select(TrainingJob).where(TrainingJob.dataset_id.in_(dataset_ids))
                )
            ).scalars().all()
            training_job_ids.update(job.id for job in jobs)
        if training_job_ids:
            patches = (
                await session.execute(
                    select(PatchRelease).where(PatchRelease.training_job_id.in_(training_job_ids))
                )
            ).scalars().all()
            patch_ids.update(patch.id for patch in patches)
        if patch_ids:
            graphs = (
                await session.execute(
                    select(GraphRelease).where(GraphRelease.organization_id == organization_id)
                )
            ).scalars().all()
            graph_ids.update(graph.id for graph in graphs if set(graph.patch_ids) & patch_ids)

        return {
            "target_type": target_type,
            "target_id": target_id,
            "affected_dataset_ids": sorted(dataset_ids),
            "affected_training_job_ids": sorted(training_job_ids),
            "affected_patch_ids": sorted(patch_ids),
            "affected_graph_release_ids": sorted(graph_ids),
            "recommended_strategy": "localized_retraining" if patch_ids else "artifact_exclusion",
            "guarantee": "Impact analysis is lineage-based and does not prove complete neural erasure.",
        }
