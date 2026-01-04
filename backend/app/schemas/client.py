"""
Schemas Pydantic para validação de entrada/saída da entidade Client.
"""
from pydantic import BaseModel, Field, field_validator, field_serializer
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
    
    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v) -> Optional[str]:
        """Converte string vazia para None."""
        if v == "" or v is None:
            return None
        return v
    
    @field_validator('birth_date', mode='before')
    @classmethod
    def validate_birth_date(cls, v) -> Optional[date]:
        """Converte string vazia para None e garante conversão correta de string para date."""
        if v == "" or v is None:
            return None
        # Se já é um objeto date, retornar como está
        if isinstance(v, date):
            return v
        # Se é uma string no formato YYYY-MM-DD, converter diretamente
        if isinstance(v, str):
            # Evitar problemas de timezone: parsear diretamente YYYY-MM-DD
            try:
                parts = v.split('-')
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    return date(year, month, day)
            except (ValueError, AttributeError):
                pass
        return v


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
        if v is None or v == "":
            return v
        phone_clean = ''.join(filter(str.isdigit, v))
        if len(phone_clean) < 10:
            raise ValueError("Telefone deve conter pelo menos 10 dígitos")
        return phone_clean
    
    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v) -> Optional[str]:
        """Converte string vazia para None."""
        if v == "" or v is None:
            return None
        return v
    
    @field_validator('birth_date', mode='before')
    @classmethod
    def validate_birth_date(cls, v) -> Optional[date]:
        """Converte string vazia para None e garante conversão correta de string para date."""
        if v == "" or v is None:
            return None
        # Se já é um objeto date, retornar como está
        if isinstance(v, date):
            return v
        # Se é uma string no formato YYYY-MM-DD, converter diretamente
        if isinstance(v, str):
            # Evitar problemas de timezone: parsear diretamente YYYY-MM-DD
            try:
                parts = v.split('-')
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    return date(year, month, day)
            except (ValueError, AttributeError):
                pass
        return v


class ClientResponse(ClientBase):
    """Schema de resposta para Client."""
    id: UUID
    tenant_id: UUID

    @field_serializer('birth_date')
    def serialize_birth_date(self, value: Optional[date], _info) -> Optional[str]:
        """Serializa birth_date como string YYYY-MM-DD (sem timezone)."""
        if value is None:
            return None
        return value.isoformat() if isinstance(value, date) else str(value)

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
    
    @field_serializer('birth_date')
    def serialize_birth_date(self, value: date, _info) -> str:
        """Serializa birth_date como string YYYY-MM-DD (sem timezone)."""
        return value.isoformat() if isinstance(value, date) else str(value)
    
    class Config:
        from_attributes = True

