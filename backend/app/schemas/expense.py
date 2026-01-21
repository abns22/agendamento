"""
Schemas Pydantic para a entidade Expense (Despesa).
"""
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from decimal import Decimal
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentMethodEnum(str, Enum):
    """Enum para métodos de pagamento de despesas."""
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    PIX = "PIX"
    BANK_TRANSFER = "BANK_TRANSFER"


class ExpenseBase(BaseModel):
    """Schema base para Expense."""
    description: str = Field(..., min_length=1, description="Descrição da despesa (Ex: 'Conta de Luz')")
    item_name: Optional[str] = Field(None, max_length=200, description="Nome do item comprado (opcional)")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Valor da despesa (deve ser positivo)")
    payment_method: PaymentMethodEnum = Field(..., description="Método de pagamento")
    payment_date: datetime = Field(..., description="Data em que o dinheiro saiu do caixa")
    category: Optional[str] = Field(None, max_length=100, description="Categoria (ex: 'FIXO', 'VARIAVEL')")


class ExpenseCreate(ExpenseBase):
    """Schema para criação de Expense."""
    pass


class ExpenseUpdate(BaseModel):
    """Schema para atualização de Expense."""
    description: Optional[str] = Field(None, min_length=1)
    item_name: Optional[str] = Field(None, max_length=200)
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    payment_method: Optional[PaymentMethodEnum] = None
    payment_date: Optional[datetime] = None
    category: Optional[str] = Field(None, max_length=100)


class ExpenseResponse(ExpenseBase):
    """Schema de resposta para Expense."""
    id: UUID
    tenant_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

