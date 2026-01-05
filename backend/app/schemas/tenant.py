"""
Schemas Pydantic para validação de entrada/saída da entidade Tenant.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime


class TenantBase(BaseModel):
    """Schema base para Tenant."""
    slug: str = Field(..., min_length=3, max_length=100, description="Slug único da empresa (ex: 'estudio-bella')")
    whatsapp_phone_id: Optional[str] = Field(None, max_length=50, description="ID do número de telefone no WhatsApp Business")
    stripe_subscription_id: Optional[str] = Field(None, max_length=100, description="ID da assinatura no Stripe")
    name: Optional[str] = Field(None, max_length=200, description="Nome do estúdio (ex: 'Estúdio Bella')")
    logo_url: Optional[str] = Field(None, max_length=500, description="URL da logo do estúdio")
    description: Optional[str] = Field(None, description="Breve descrição do estúdio")
    address: Optional[str] = Field(None, description="Endereço físico do estúdio")
    phone_contact: Optional[str] = Field(None, max_length=20, description="Número de telefone público para contato")
    schedule_display_text: Optional[str] = Field(None, max_length=200, description="Texto amigável do horário (ex: 'Segunda a Sexta, 09:00 - 18:00')")
    notification_days: Optional[int] = Field(None, ge=1, le=30, description="Número de dias para buscar agendamentos futuros (padrão: 3)")


class TenantCreate(TenantBase):
    """Schema para criação de um novo Tenant."""
    pass


class TenantUpdate(BaseModel):
    """Schema para atualização parcial de Tenant."""
    slug: Optional[str] = Field(None, min_length=3, max_length=100)
    whatsapp_phone_id: Optional[str] = Field(None, max_length=50)
    stripe_subscription_id: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    name: Optional[str] = Field(None, max_length=200)
    logo_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    address: Optional[str] = None
    phone_contact: Optional[str] = Field(None, max_length=20)
    schedule_display_text: Optional[str] = Field(None, max_length=200)
    notification_days: Optional[int] = Field(None, ge=1, le=30, description="Número de dias para buscar agendamentos futuros (padrão: 3)")


class TenantResponse(TenantBase):
    """Schema de resposta para Tenant."""
    id: UUID
    is_active: bool
    is_exempt: bool = Field(default=False, description="Se True, tenant está isento de pagamento")
    
    class Config:
        from_attributes = True


