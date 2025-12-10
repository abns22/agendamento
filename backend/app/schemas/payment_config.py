"""
Schemas Pydantic para configurações de pagamento.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional, List
from enum import Enum


class TaxTypeEnum(str, Enum):
    """Tipo de taxa."""
    PERCENT = "%"
    FIXED = "R$"


# ============================================
# PaymentMethodConfig Schemas
# ============================================

class PaymentMethodConfigBase(BaseModel):
    """Schema base para PaymentMethodConfig."""
    method_name: str = Field(..., min_length=1, max_length=100, description="Nome da forma de pagamento")
    is_editable: bool = Field(default=True, description="Se a forma de pagamento pode ser editada")
    max_installments: Optional[int] = Field(None, ge=1, le=12, description="Máximo de parcelas (apenas para crédito)")
    debit_tax_type: Optional[str] = Field(None, description="Tipo de taxa de débito: '%' ou 'R$'")
    debit_tax_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Valor da taxa de débito")


class PaymentMethodConfigCreate(PaymentMethodConfigBase):
    """Schema para criação de PaymentMethodConfig."""
    pass


class PaymentMethodConfigUpdate(BaseModel):
    """Schema para atualização de PaymentMethodConfig."""
    is_editable: Optional[bool] = None
    max_installments: Optional[int] = Field(None, ge=1, le=12)
    debit_tax_type: Optional[str] = None
    debit_tax_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class PaymentMethodConfigResponse(PaymentMethodConfigBase):
    """Schema de resposta para PaymentMethodConfig."""
    id: UUID
    tenant_id: UUID
    
    class Config:
        from_attributes = True


# ============================================
# PaymentInstallmentConfig Schemas
# ============================================

class PaymentInstallmentConfigBase(BaseModel):
    """Schema base para PaymentInstallmentConfig."""
    installments_count: int = Field(..., ge=2, le=12, description="Número de parcelas")
    tax_type: str = Field(..., description="Tipo de taxa: '%' ou 'R$'")
    tax_value: Decimal = Field(..., ge=0, decimal_places=2, description="Valor da taxa")


class PaymentInstallmentConfigCreate(PaymentInstallmentConfigBase):
    """Schema para criação de PaymentInstallmentConfig."""
    payment_method_id: UUID = Field(..., description="ID da forma de pagamento (Cartão de Crédito)")


class PaymentInstallmentConfigUpdate(BaseModel):
    """Schema para atualização de PaymentInstallmentConfig."""
    tax_type: Optional[str] = None
    tax_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class PaymentInstallmentConfigResponse(PaymentInstallmentConfigBase):
    """Schema de resposta para PaymentInstallmentConfig."""
    id: UUID
    payment_method_id: UUID
    
    class Config:
        from_attributes = True


# ============================================
# Schemas para resposta completa com relacionamentos
# ============================================

class PaymentMethodConfigWithInstallments(PaymentMethodConfigResponse):
    """Schema de resposta com lista de configurações de parcelamento."""
    installments: List[PaymentInstallmentConfigResponse] = []

