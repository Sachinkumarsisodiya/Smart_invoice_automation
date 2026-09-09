from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.analytics import (
    DashboardKPIsResponse,
    MonthlyCashflowItem,
    CategoryDistributionItem,
    StatusDistributionItem,
    TopVendorItem,
    RecentActivityItem
)
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/stats", response_model=DashboardKPIsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get high-level business financial KPIs."""
    return AnalyticsService.get_dashboard_kpis(db=db)


@router.get("/monthly-cashflow", response_model=List[MonthlyCashflowItem])
def get_monthly_cashflow(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get monthly trend comparing billed invoices, settled payments, and expenses."""
    return AnalyticsService.get_monthly_cashflow(db=db, num_months=months)


@router.get("/category-distribution", response_model=List[CategoryDistributionItem])
def get_category_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get spend distribution across expense and vendor categories."""
    return AnalyticsService.get_category_distribution(db=db)


@router.get("/status-distribution", response_model=List[StatusDistributionItem])
def get_status_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get count and volume breakdown by invoice lifecycle status."""
    return AnalyticsService.get_status_distribution(db=db)


@router.get("/top-vendors", response_model=List[TopVendorItem])
def get_top_vendors(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get top suppliers ranked by total invoiced volume."""
    return AnalyticsService.get_top_vendors(db=db, limit=limit)


@router.get("/recent-activity", response_model=List[RecentActivityItem])
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get unified chronological timeline of latest invoices, settlements, and expenses."""
    return AnalyticsService.get_recent_activity(db=db, limit=limit)
