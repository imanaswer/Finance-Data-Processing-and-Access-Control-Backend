import math
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin, require_viewer
from app.database import get_db
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.transaction import (
    PaginatedTransactions,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get(
    "",
    response_model=PaginatedTransactions,
    summary="List transactions [Viewer+]",
)
def list_transactions(
    # Pagination
    page: int = Query(1, ge=1, description="Page number, starts at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    # Filters
    type: Optional[TransactionType] = Query(None, description="Filter by income or expense"),
    category: Optional[str] = Query(None, description="Filter by category (partial match)"),
    date_from: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    # Full-text search across category and notes
    search: Optional[str] = Query(None, description="Search in category and notes"),
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
):
    """
    Return a paginated, filterable list of financial records.
    Accessible to all authenticated users (viewer, analyst, admin).
    """
    query = db.query(Transaction).filter(Transaction.is_deleted == False)

    if type:
        query = query.filter(Transaction.type == type)
    if category:
        query = query.filter(Transaction.category.ilike(f"%{category}%"))
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if search:
        query = query.filter(
            or_(
                Transaction.category.ilike(f"%{search}%"),
                Transaction.notes.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    items = (
        query.order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedTransactions(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
        items=items,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get a transaction [Viewer+]",
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
):
    """Retrieve a single transaction by ID. All authenticated users."""
    txn = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.is_deleted == False)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return txn


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transaction [Admin]",
)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new financial record. Admin only."""
    txn = Transaction(**payload.model_dump(), created_by=current_user.id)
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update a transaction [Admin]",
)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Update one or more fields on an existing record. Admin only."""
    txn = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.is_deleted == False)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)

    db.commit()
    db.refresh(txn)
    return txn


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction [Admin]",
)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Soft-delete a transaction (sets is_deleted=True).
    The record is retained in the database for audit purposes.
    Admin only.
    """
    txn = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.is_deleted == False)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    txn.is_deleted = True
    db.commit()
