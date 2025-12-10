"""
Schemas Pydantic para dados públicos do Tenant.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class PublicTenantResponse(BaseModel):
    """
    Schema de resposta para dados públicos do tenant.
    
    Este schema contém APENAS os dados que devem ser expostos publicamente
    na página de agendamento, sem informações sensíveis como IDs internos,
    assinaturas, etc.
    """
    id: UUID = Field(..., description="ID do tenant")
    name: Optional[str] = Field(None, description="Nome do estúdio")
    slug: str = Field(..., description="Slug único do tenant")
    logo_url: Optional[str] = Field(None, description="URL da logo do estúdio")
    description: Optional[str] = Field(None, description="Breve descrição do estúdio")
    address: Optional[str] = Field(None, description="Endereço físico do estúdio")
    phone_contact: Optional[str] = Field(None, description="Número de telefone público para contato")
    schedule_display_text: Optional[str] = Field(None, description="Texto amigável do horário de funcionamento")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "Estúdio Bella",
                "slug": "estudio-bella",
                "logo_url": "https://example.com/logo.png",
                "description": "Estúdio de estética especializado em tratamentos faciais e corporais.",
                "address": "Rua das Flores, 123 - São Paulo, SP",
                "phone_contact": "5511999999999",
                "schedule_display_text": "Segunda a Sexta, 09:00 - 18:00"
            }
        }

