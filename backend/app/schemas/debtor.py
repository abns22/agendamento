"""
Schemas Pydantic para a entidade Debtor (Devedor).
"""
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional
from datetime import datetime


class DebtorBase(BaseModel):
    """Schema base para Debtor."""
    client_name: str = Field(..., min_length=1, max_length=200, description="Nome do cliente devedor")
    client_phone: Optional[str] = Field(None, max_length=20, description="Telefone do cliente")
    due_date: datetime = Field(..., description="Data de vencimento (UTC)")
    value_due: Decimal = Field(..., ge=0, decimal_places=2, description="Valor devido")


class DebtorCreate(DebtorBase):
    """Schema para criação de Debtor (via finalização com pagamento futuro)."""
    pass


class DebtorResponse(DebtorBase):
    """Schema de resposta para Debtor."""
    id: UUID
    transaction_id: UUID
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SettleDebtorRequest(BaseModel):
    """Schema para baixa de devedor."""
    payment_method_id: UUID = Field(..., description="ID da forma de pagamento usada para pagar")
    installments: Optional[int] = Field(None, ge=1, le=12, description="Número de parcelas (apenas para crédito)")


class SettleDebtorResponse(BaseModel):
    """Schema de resposta para baixa de devedor."""
    debtor: DebtorResponse
    payment_entry: dict  # PaymentEntry criado
    message: str = "Dívida quitada com sucesso"

