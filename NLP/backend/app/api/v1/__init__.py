from fastapi import APIRouter

from app.api.v1 import datasets, query, analytics, dashboards, reports

router = APIRouter()
router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
router.include_router(query.router, prefix="/query", tags=["NLP Query"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(dashboards.router, prefix="/dashboards", tags=["Dashboards"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
