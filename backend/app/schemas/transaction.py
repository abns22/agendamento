"""
Schemas Pydantic para Transaction e PaymentEntry.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


# ============================================
# PaymentEntry Schemas
# ============================================

class PaymentEntryBase(BaseModel):
    """Schema base para PaymentEntry."""
    payment_method_id: UUID = Field(..., description="ID da forma de pagamento")
    value_paid: Decimal = Field(..., ge=0, decimal_places=2, description="Valor parcial pago nesta forma")
    installments: Optional[int] = Field(None, ge=1, le=12, description="Número de parcelas (apenas para crédito)")


class PaymentEntryCreate(PaymentEntryBase):
    """Schema para criação de PaymentEntry."""
    pass


class PaymentEntryResponse(PaymentEntryBase):
    """Schema de resposta para PaymentEntry."""
    id: UUID
    transaction_id: UUID
    is_bank_account: bool
    
    class Config:
        from_attributes = True


# ============================================
# Transaction Schemas
# ============================================

class TransactionBase(BaseModel):
    """Schema base para Transaction."""
    appointment_id: UUID = Field(..., description="ID do agendamento")
    gross_value: Decimal = Field(..., ge=0, decimal_places=2, description="Valor bruto (antes das taxas)")
    net_value: Decimal = Field(..., ge=0, decimal_places=2, description="Valor líquido (após taxas)")
    total_cost: Decimal = Field(..., ge=0, decimal_places=2, description="Soma dos custos fixos dos serviços")
    total_profit: Decimal = Field(..., decimal_places=2, description="Lucro (net_value - total_cost)")
    additional_cost: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Custo adicional opcional")


class TransactionCreate(BaseModel):
    """Schema para criação de Transaction (via finalização)."""
    payment_entries: List[PaymentEntryCreate] = Field(..., min_length=1, description="Lista de formas de pagamento")
    additional_cost: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Custo adicional opcional")
    is_paid: bool = Field(True, description="True se foi pago, False se é a prazo (pagamento futuro)")


class TransactionResponse(TransactionBase):
    """Schema de resposta para Transaction."""
    id: UUID
    tenant_id: UUID
    date_time: datetime
    payment_entries: List[PaymentEntryResponse] = []
    
    class Config:
        from_attributes = True


# ============================================
# Schema para Finalização
# ============================================

class FinalizeAppointmentRequest(BaseModel):
    """Schema para requisição de finalização de agendamento."""
    payment_entries: List[PaymentEntryCreate] = Field(default=[], description="Lista de formas de pagamento (vazia se is_paid=False)")
    additional_cost: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Custo adicional opcional")
    is_paid: bool = Field(True, description="True se foi pago, False se é a prazo (pagamento futuro)")
    # Campos para pagamento futuro (quando is_paid=False)
    client_name: Optional[str] = Field(None, max_length=200, description="Nome do cliente (obrigatório se is_paid=False)")
    client_phone: Optional[str] = Field(None, max_length=20, description="Telefone do cliente (opcional)")
    due_date: Optional[datetime] = Field(None, description="Data de vencimento (obrigatório se is_paid=False)")
    value_due: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Valor devido (opcional, se não fornecido usa o valor total do serviço)")


class FinalizeAppointmentResponse(BaseModel):
    """Schema de resposta para finalização de agendamento."""
    transaction: TransactionResponse
    appointment: dict  # AppointmentResponse simplificado
    message: str = "Agendamento finalizado com sucesso"

