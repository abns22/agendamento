"""
Schemas Pydantic para Relatórios e Caixa.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


# ============================================
# Cash Summary Schemas
# ============================================

class PaymentMethodSummary(BaseModel):
    """Resumo por forma de pagamento."""
    method_name: str
    total_received: Decimal
    is_bank_account: bool


class CashSummaryResponse(BaseModel):
    """Resumo do caixa para um período."""
    period_start: datetime
    period_end: datetime
    period_type: str  # 'daily' ou 'monthly'
    
    # Faturamento
    gross_revenue: Decimal = Field(..., description="Faturamento bruto (antes das taxas)")
    net_revenue: Decimal = Field(..., description="Faturamento líquido (após taxas)")
    
    # Custos e Lucro
    total_service_cost: Decimal = Field(..., description="Custo total dos serviços")
    total_additional_cost: Decimal = Field(..., description="Custo adicional total")
    total_cost: Decimal = Field(..., description="Custo total (serviços + adicional)")
    total_profit: Decimal = Field(..., description="Lucro total (net_revenue - total_cost)")
    
    # Despesas (será implementado quando Expense for criado)
    total_expenses: Decimal = Field(default=Decimal('0.00'), description="Despesas totais")
    
    # Resumo por forma de pagamento
    payment_methods_summary: List[PaymentMethodSummary] = []
    
    # Contadores
    total_transactions: int = Field(..., description="Número total de transações")
    total_appointments: int = Field(..., description="Número total de agendamentos finalizados")


# ============================================
# Transaction Detail Schemas
# ============================================

class PaymentEntryDetail(BaseModel):
    """Detalhe de uma entrada de pagamento."""
    id: UUID
    payment_method_name: str
    value_paid: Decimal
    installments: Optional[int] = None
    is_bank_account: bool


class TransactionDetailResponse(BaseModel):
    """Resposta detalhada de uma transação."""
    id: UUID
    appointment_id: UUID
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_name: Optional[str] = None
    date_time: datetime
    gross_value: Decimal
    net_value: Decimal
    total_cost: Decimal
    total_profit: Decimal
    additional_cost: Optional[Decimal] = None
    payment_entries: List[PaymentEntryDetail] = []


class TransactionsListResponse(BaseModel):
    """Lista de transações com filtros."""
    transactions: List[TransactionDetailResponse]
    total_count: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

