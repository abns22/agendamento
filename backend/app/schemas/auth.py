"""
Schemas Pydantic para autenticação.
"""
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from typing import Optional


class UserRegister(BaseModel):
    """Schema para registro de novo usuário."""
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=8, description="Senha (mínimo 8 caracteres)")
    tenant_id: Optional[UUID] = Field(None, description="UUID do tenant existente (opcional)")
    tenant_slug: Optional[str] = Field(None, description="Slug do tenant existente (opcional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@estudio.com",
                "password": "senha123456",
                "tenant_id": None,
                "tenant_slug": None
            }
        }


class UserLogin(BaseModel):
    """Schema para login de usuário."""
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., description="Senha")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@estudio.com",
                "password": "senha123456"
            }
        }


class TokenResponse(BaseModel):
    """Schema de resposta com tokens JWT."""
    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Tipo do token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class UserResponse(BaseModel):
    """Schema de resposta para dados do usuário."""
    id: UUID
    email: str
    tenant_id: UUID
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "admin@estudio.com",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "role": "ADMIN",
                "is_active": True
            }
        }


