"""
Schemas Pydantic para operações de faturamento (Stripe).
"""
from pydantic import BaseModel, Field
from typing import Optional


class CreateCheckoutSessionRequest(BaseModel):
    """Schema para criar sessão de checkout."""
    success_url: Optional[str] = Field(
        None,
        description="URL de redirecionamento após pagamento bem-sucedido. Se não fornecido, usa URL padrão."
    )
    cancel_url: Optional[str] = Field(
        None,
        description="URL de redirecionamento se o usuário cancelar. Se não fornecido, usa URL padrão."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success_url": "https://meusite.com/admin/billing/success",
                "cancel_url": "https://meusite.com/admin/billing/cancel"
            }
        }


class CreateCheckoutSessionResponse(BaseModel):
    """Schema de resposta para criação de checkout session."""
    checkout_url: str = Field(..., description="URL de redirecionamento para o checkout do Stripe")
    session_id: str = Field(..., description="ID da sessão de checkout")
    
    class Config:
        json_schema_extra = {
            "example": {
                "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
                "session_id": "cs_test_..."
            }
        }


class ManageSubscriptionRequest(BaseModel):
    """Schema para gerenciar assinatura (abrir portal de billing)."""
    return_url: Optional[str] = Field(
        None,
        description="URL de retorno após sair do portal. Se não fornecido, usa URL padrão."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "return_url": "https://meusite.com/admin/billing"
            }
        }


class ManageSubscriptionResponse(BaseModel):
    """Schema de resposta para portal de billing."""
    portal_url: str = Field(..., description="URL de redirecionamento para o portal de billing do Stripe")
    session_id: str = Field(..., description="ID da sessão do portal")
    
    class Config:
        json_schema_extra = {
            "example": {
                "portal_url": "https://billing.stripe.com/p/session/...",
                "session_id": "bps_..."
            }
        }


class BillingStatusResponse(BaseModel):
    """Schema de resposta para status da assinatura."""
    is_active: bool = Field(..., description="Se a assinatura está ativa")
    has_subscription: bool = Field(..., description="Se o tenant possui uma assinatura cadastrada")
    subscription_id: Optional[str] = Field(None, description="ID da assinatura no Stripe (se existir)")
    subscription_status: Optional[str] = Field(None, description="Status da assinatura no Stripe (active, canceled, etc)")
    current_period_end: Optional[int] = Field(None, description="Timestamp do fim do período atual (se existir)")
    is_exempt: bool = Field(default=False, description="Se True, tenant está isento de pagamento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_active": True,
                "has_subscription": True,
                "subscription_id": "sub_1234567890",
                "subscription_status": "active",
                "current_period_end": 1735689600
            }
        }
