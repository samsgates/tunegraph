from __future__ import annotations

from fastapi import APIRouter

from tunegraph.api.routes import (
    audit,
    auth,
    capabilities,
    contracts,
    datasets,
    deployments,
    graphs,
    health,
    inference,
    models,
    patches,
    removals,
    traces,
    training,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(models.router)
api_router.include_router(datasets.router)
api_router.include_router(capabilities.router)
api_router.include_router(training.router)
api_router.include_router(contracts.router)
api_router.include_router(patches.router)
api_router.include_router(graphs.router)
api_router.include_router(deployments.router)
api_router.include_router(traces.router)
api_router.include_router(removals.router)
api_router.include_router(audit.router)

root_router = APIRouter()
root_router.include_router(inference.router)
