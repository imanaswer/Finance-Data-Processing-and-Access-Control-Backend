from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.dependencies import require_analyst
from app.database import get_db
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.transaction import TransactionResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _base_query(db: Session, date_from: Optional[date], date_to: Optional[date]):
    """Helper: active transactions optionally narrowed to a date window."""
    q = db.query(Transaction).filter(Transaction.is_deleted == False)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    return q


@router.get("/summary", summary="Overall financial summary [Analyst+]")
def get_summary(
    date_from: Optional[date] = Query(None, description="Start of date window"),
    date_to: Optional[date] = Query(None, description="End of date window"),
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst),
):
    """
    Return total income, total expenses, net balance, and transaction count.
    Supports an optional date window. Analyst and Admin only.
    """
    rows = _base_query(db, date_from, date_to).all()

    total_income = sum(r.amount for r in rows if r.type == TransactionType.INCOME)
    total_expenses = sum(r.amount for r in rows if r.type == TransactionType.EXPENSE)

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_balance": round(total_income - total_expenses, 2),
        "transaction_count": len(rows),
        "date_from": date_from,
        "date_to": date_to,
    }


@router.get("/categories", summary="Category-wise totals [Analyst+]")
def get_category_breakdown(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst),
):
    """
    Return the sum and count of transactions grouped by category and type.
    Useful for building a category breakdown chart. Analyst and Admin only.
    """
    q = (
        db.query(
            Transaction.category,
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .filter(Transaction.is_deleted == False)
        .group_by(Transaction.category, Transaction.type)
    )
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)

    return [
        {
            "category": row.category,
            "type": row.type,
            "total": round(row.total, 2),
            "count": row.count,
        }
        for row in q.order_by(Transaction.category).all()
    ]


@router.get("/trends/monthly", summary="Monthly income vs expense trend [Analyst+]")
def get_monthly_trends(
    year: Optional[int] = Query(None, description="Filter to a specific year, e.g. 2024"),
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst),
):
    """
    Return monthly income and expense totals suitable for a line/bar chart.
    Results are grouped by year-month and sorted chronologically.
    Analyst and Admin only.
    """
    q = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.is_deleted == False)
        .group_by("year", "month", Transaction.type)
    )
    if year:
        q = q.filter(extract("year", Transaction.date) == year)

    rows = q.order_by("year", "month").all()

    # Pivot rows into {month: {income, expense}} shape
    pivot: dict = {}
    for row in rows:
        key = f"{int(row.year)}-{int(row.month):02d}"
        if key not in pivot:
            pivot[key] = {"month": key, "income": 0.0, "expense": 0.0}
        pivot[key][row.type.value] = round(row.total, 2)

    return list(pivot.values())


@router.get(
    "/recent",
    response_model=list[TransactionResponse],
    summary="Recent transactions [Analyst+]",
)
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent records to return"),
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst),
):
    """
    Return the most recent N transactions ordered by date then creation time.
    Analyst and Admin only.
    """
    return (
        db.query(Transaction)
        .filter(Transaction.is_deleted == False)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
