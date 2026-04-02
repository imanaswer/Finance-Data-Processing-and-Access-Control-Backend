from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.transaction import TransactionType


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Amount must be positive")
    type: TransactionType
    category: str = Field(..., min_length=1, max_length=100)
    date: date
    notes: Optional[str] = Field(None, max_length=1000)


class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    type: Optional[TransactionType] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Response bodies
# ---------------------------------------------------------------------------

class TransactionResponse(BaseModel):
    id: int
    amount: float
    type: TransactionType
    category: str
    date: date
    notes: Optional[str]
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTransactions(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[TransactionResponse]
