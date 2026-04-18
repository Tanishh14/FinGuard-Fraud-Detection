from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.dependencies import get_db, require_admin, require_analyst_or_admin
from app.analytics.service import AnalyticsService

router = APIRouter()

def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)

@router.get("/dashboard/stats")
def get_dashboard_stats(
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Results for System Health Summary (KPI Cards) & Live Graph."""
    return service.get_kpi_dashboard()

@router.get("/dashboard/top-entities")
def get_top_entities(
    limit: int = 5,
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Ranked tables for Users, Merchants, Devices by risk."""
    return service.get_risk_entities(limit)

@router.get("/geo")
def get_geo_stats(
    days: int = 30,
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Returns aggregated transaction data by location for mapping."""
    return service.get_geo_metrics(days)

@router.get("/dashboard/model-performance")
def get_model_performance(
    days: int = Query(30, ge=1, le=365),
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Returns confusion matrix and accuracy metrics for the ML models."""
    return service.get_model_performance(days)

@router.get("/dashboard/case-stats")
def get_case_dashboard(
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """High-level summary of investigation cases and review backlog."""
    return service.get_case_dashboard()

@router.get("/trends")
def get_risk_trends(
    days: int = Query(7, ge=1, le=90),
    threshold: float = Query(0.5, ge=0, le=1.0),
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Returns time-series data of high-risk vs total transactions."""
    return service.get_risk_trends(days, threshold)

@router.get("/gauges")
def get_risk_gauges(
    threshold: float = Query(0.9, ge=0, le=1.0),
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Risk distribution for gauge charts."""
    return service.get_risk_gauges(threshold)

@router.get("/merchants")
def get_top_merchants(
    limit: int = Query(5, ge=1, le=50),
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Ranked merchants by risk and volume."""
    return service.get_top_merchants(limit)

@router.get("/forensics")
def get_forensics_summary(
    service: AnalyticsService = Depends(get_analytics_service),
    admin=Depends(require_admin)
):
    """Returns analytics for forensics investigations."""
    return service.get_forensic_summary()

@router.get("/reports/download")
def download_transaction_report(
    time_range: str = Query("7d", regex="^(24h|7d|monthly|yearly)$"),
    username: Optional[str] = None,
    service: AnalyticsService = Depends(get_analytics_service),
    analyst=Depends(require_analyst_or_admin)
):
    """Generates and returns a PDF transaction report."""
    pdf_bytes = service.generate_transaction_report(time_range, username)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=finguard_report_{time_range}.pdf"
        }
    )
