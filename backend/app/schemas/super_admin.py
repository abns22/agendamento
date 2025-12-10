"""
Schemas Pydantic para operações de Super Admin.
"""
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from typing import Optional


class OnboardTenantRequest(BaseModel):
    """Schema para onboarding de novo tenant."""
    company_name: str = Field(..., min_length=3, max_length=100, description="Nome da empresa/estúdio")
    slug: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-z0-9-]+$', description="Slug único (apenas letras minúsculas, números e hífens)")
    admin_name: str = Field(..., min_length=2, max_length=100, description="Nome do administrador")
    admin_email: EmailStr = Field(..., description="Email do administrador")
    notification_phone: Optional[str] = Field(None, description="Telefone de notificação (formato internacional)")
    password: Optional[str] = Field(None, min_length=8, description="Senha do administrador (opcional, será gerada se não fornecida)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Estúdio Bella",
                "slug": "estudio-bella",
                "admin_name": "Maria Silva",
                "admin_email": "maria@estudiobella.com",
                "notification_phone": "5511999999999",
                "password": None  # Será gerada automaticamente
            }
        }


class OnboardTenantResponse(BaseModel):
    """Schema de resposta para onboarding de tenant."""
    tenant_id: UUID = Field(..., description="ID do tenant criado")
    tenant_slug: str = Field(..., description="Slug do tenant")
    company_name: str = Field(..., description="Nome da empresa")
    admin_id: UUID = Field(..., description="ID do administrador criado")
    admin_email: str = Field(..., description="Email do administrador")
    temporary_password: str = Field(..., description="Senha temporária gerada")
    message: str = Field(..., description="Mensagem de sucesso")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "tenant_slug": "estudio-bella",
                "company_name": "Estúdio Bella",
                "admin_id": "123e4567-e89b-12d3-a456-426614174002",
                "admin_email": "maria@estudiobella.com",
                "temporary_password": "TempPass123!",
                "message": "Tenant criado com sucesso. Senha temporária gerada."
            }
        }

