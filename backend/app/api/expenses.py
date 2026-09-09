import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseSummaryResponse
from app.schemas.common import PaginatedResponse
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=PaginatedResponse[ExpenseResponse])
def list_expenses(
    category: Optional[str] = Query(None, description="Filter by expense category"),
    vendor_id: Optional[uuid.UUID] = Query(None, description="Filter by vendor"),
    payment_method: Optional[str] = Query(None, description="Filter by payment method"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search description or category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists expenses with filters and pagination."""
    skip = (page - 1) * page_size
    expenses, total = ExpenseService.get_expenses(
        db=db,
        category=category,
        vendor_id=vendor_id,
        payment_method=payment_method,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=page_size
    )
    return PaginatedResponse.create(
        items=[ExpenseResponse.model_validate(e) for e in expenses],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/summary", response_model=ExpenseSummaryResponse)
def get_expense_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculates overall expense statistics and category-wise spend distribution."""
    return ExpenseService.get_expense_summary(db=db)


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves single expense by ID."""
    expense = ExpenseService.get_expense_by_id(db=db, expense_id=expense_id)
    return ExpenseResponse.model_validate(expense)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.STAFF]))
):
    """Records a new operational expense (Admin or Staff only)."""
    expense = ExpenseService.create_expense(db=db, data=data, user_id=current_user.id)
    return ExpenseResponse.model_validate(expense)


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.STAFF]))
):
    """Updates an existing expense (Admin or Staff only)."""
    expense = ExpenseService.update_expense(db=db, expense_id=expense_id, data=data, user_id=current_user.id)
    return ExpenseResponse.model_validate(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_200_OK)
def delete_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Deletes an expense record (Admin only)."""
    ExpenseService.delete_expense(db=db, expense_id=expense_id, user_id=current_user.id)
    return {"message": "Expense deleted successfully"}
