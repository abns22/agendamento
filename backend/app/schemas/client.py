"""
Schemas Pydantic para validação de entrada/saída da entidade Client.
"""
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from typing import Optional
from datetime import date


class ClientBase(BaseModel):
    """Schema base para Client."""
    name: str = Field(..., min_length=2, max_length=200, description="Nome completo do cliente")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Número de telefone do cliente")
    email: Optional[str] = Field(None, max_length=200, description="Email do cliente (opcional)")
    birth_date: Optional[date] = Field(None, description="Data de nascimento (para aniversários)")
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Valida e normaliza o telefone."""
        # Remove caracteres não numéricos
        phone_clean = ''.join(filter(str.isdigit, v))
        if len(phone_clean) < 10:
            raise ValueError("Telefone deve conter pelo menos 10 dígitos")
        return phone_clean


class ClientCreate(ClientBase):
    """Schema para criação de Client."""
    pass


class ClientUpdate(BaseModel):
    """Schema para atualização parcial de Client."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    birth_date: Optional[date] = None
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Valida e normaliza o telefone."""
        if v is None:
            return v
        phone_clean = ''.join(filter(str.isdigit, v))
        if len(phone_clean) < 10:
            raise ValueError("Telefone deve conter pelo menos 10 dígitos")
        return phone_clean


class ClientResponse(ClientBase):
    """Schema de resposta para Client."""
    id: UUID
    tenant_id: UUID

    class Config:
        from_attributes = True


class BirthdayClientResponse(BaseModel):
    """Schema de resposta para aniversariantes."""
    id: UUID
    name: str
    phone_number: str
    email: Optional[str] = None
    birth_date: date
    day_of_month: int = Field(..., description="Dia do mês do aniversário")
    
    class Config:
        from_attributes = True

