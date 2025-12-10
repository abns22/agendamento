"""
Schemas Pydantic para a entidade Expense (Despesa).
"""
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional
from datetime import datetime


class ExpenseBase(BaseModel):
    """Schema base para Expense."""
    description: str = Field(..., min_length=1, description="Descrição da despesa")
    value: Decimal = Field(..., ge=0, decimal_places=2, description="Valor da despesa")
    category: Optional[str] = Field(None, max_length=100, description="Categoria da despesa (ex: Aluguel, Material, Salário)")
    date_time: Optional[datetime] = Field(None, description="Data/hora da despesa (UTC). Se não fornecido, usa a data atual.")


class ExpenseCreate(ExpenseBase):
    """Schema para criação de Expense."""
    pass


class ExpenseUpdate(BaseModel):
    """Schema para atualização de Expense."""
    description: Optional[str] = Field(None, min_length=1)
    value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    category: Optional[str] = Field(None, max_length=100)
    date_time: Optional[datetime] = None


class ExpenseResponse(ExpenseBase):
    """Schema de resposta para Expense."""
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

