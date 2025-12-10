"""
Schemas Pydantic para configurações do Tenant.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import time


class TenantConfigResponse(BaseModel):
    """Schema de resposta para configurações do tenant."""
    tenant_id: UUID = Field(..., description="ID do tenant")
    slug: str = Field(..., description="Slug único do tenant")
    company_name: Optional[str] = Field(None, description="Nome da empresa (formatado do slug ou campo name)")
    notification_phone_number: Optional[str] = Field(None, description="Número de WhatsApp para notificações")
    whatsapp_phone_id: Optional[str] = Field(None, description="ID do número WhatsApp Business na Meta API")
    
    # Campos públicos editáveis
    name: Optional[str] = Field(None, description="Nome do estúdio")
    logo_url: Optional[str] = Field(None, description="URL da logo do estúdio")
    description: Optional[str] = Field(None, description="Breve descrição do estúdio")
    address: Optional[str] = Field(None, description="Endereço físico do estúdio")
    phone_contact: Optional[str] = Field(None, description="Número de telefone público para contato")
    schedule_display_text: Optional[str] = Field(None, description="Texto amigável do horário de funcionamento")
    
    # Horários de funcionamento (simplificado - horário padrão)
    default_start_time: Optional[str] = Field(None, description="Horário de abertura padrão (HH:MM)")
    default_end_time: Optional[str] = Field(None, description="Horário de fechamento padrão (HH:MM)")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "slug": "estudio-bella",
                "company_name": "Estúdio Bella",
                "notification_phone_number": "5511999999999",
                "whatsapp_phone_id": "123456789",
                "default_start_time": "09:00",
                "default_end_time": "18:00"
            }
        }


class TenantConfigUpdate(BaseModel):
    """Schema para atualização de configurações do tenant."""
    notification_phone_number: Optional[str] = Field(
        None, 
        max_length=20, 
        description="Número de WhatsApp para notificações (formato internacional, ex: 5511999999999)"
    )
    default_start_time: Optional[str] = Field(
        None,
        pattern=r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$',
        description="Horário de abertura padrão (formato HH:MM, ex: 09:00)"
    )
    default_end_time: Optional[str] = Field(
        None,
        pattern=r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$',
        description="Horário de fechamento padrão (formato HH:MM, ex: 18:00)"
    )
    # Campos públicos editáveis
    name: Optional[str] = Field(None, max_length=200, description="Nome do estúdio")
    logo_url: Optional[str] = Field(None, max_length=500, description="URL da logo do estúdio")
    description: Optional[str] = Field(None, description="Breve descrição do estúdio")
    address: Optional[str] = Field(None, description="Endereço físico do estúdio")
    phone_contact: Optional[str] = Field(None, max_length=20, description="Número de telefone público para contato")
    schedule_display_text: Optional[str] = Field(None, max_length=200, description="Texto amigável do horário (ex: 'Segunda a Sexta, 09:00 - 18:00')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "notification_phone_number": "5511999999999",
                "default_start_time": "09:00",
                "default_end_time": "18:00"
            }
        }

