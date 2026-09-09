import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse, VendorDetailResponse
from app.schemas.common import PaginatedResponse
from app.services.vendor_service import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=PaginatedResponse[VendorResponse])
def list_vendors(
    search: Optional[str] = Query(None, description="Search by name, GSTIN, or email"),
    category: Optional[str] = Query(None, description="Filter by category"),
    active_only: bool = Query(False, description="Show only active vendors"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists vendors with search, category filtering, and pagination."""
    skip = (page - 1) * page_size
    vendors, total = VendorService.get_vendors(
        db=db,
        search=search,
        category=category,
        active_only=active_only,
        skip=skip,
        limit=page_size
    )
    return PaginatedResponse.create(
        items=[VendorResponse.model_validate(v) for v in vendors],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{vendor_id}", response_model=VendorDetailResponse)
def get_vendor(
    vendor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves vendor details including aggregated financial metrics."""
    return VendorService.get_vendor_by_id(db=db, vendor_id=vendor_id)


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.STAFF]))
):
    """Creates a new vendor (Admin or Staff only)."""
    vendor = VendorService.create_vendor(db=db, data=data, user_id=current_user.id)
    return VendorResponse.model_validate(vendor)


@router.put("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: uuid.UUID,
    data: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.STAFF]))
):
    """Updates vendor details (Admin or Staff only)."""
    vendor = VendorService.update_vendor(db=db, vendor_id=vendor_id, data=data, user_id=current_user.id)
    return VendorResponse.model_validate(vendor)


@router.delete("/{vendor_id}", status_code=status.HTTP_200_OK)
def delete_vendor(
    vendor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Deletes or deactivates a vendor (Admin only)."""
    VendorService.delete_vendor(db=db, vendor_id=vendor_id, user_id=current_user.id)
    return {"message": "Vendor deleted or deactivated successfully"}
