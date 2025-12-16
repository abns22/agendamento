"""
Schemas Pydantic para a entidade Appointment (Agendamento).
"""
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional


class AppointmentCreate(BaseModel):
    """Schema para criação de um novo agendamento."""
    service_id: UUID = Field(..., description="UUID do serviço a ser agendado")
    customer_name: str = Field(..., min_length=2, max_length=200, description="Nome do cliente")
    customer_phone: str = Field(..., min_length=10, max_length=20, description="Telefone do cliente")
    start_datetime: datetime = Field(..., description="Data e hora de início do agendamento (UTC)")
    
    @field_validator('customer_phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Valida e normaliza o telefone."""
        # Remove caracteres não numéricos
        phone_clean = ''.join(filter(str.isdigit, v))
        if len(phone_clean) < 10:
            raise ValueError("Telefone deve conter pelo menos 10 dígitos")
        return phone_clean
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_id": "123e4567-e89b-12d3-a456-426614174000",
                "customer_name": "Maria Silva",
                "customer_phone": "11987654321",
                "start_datetime": "2024-01-15T10:00:00Z"
            }
        }


class ManualAppointmentCreate(BaseModel):
    """Schema para criação de agendamento manual pelo administrador."""
    service_id: UUID = Field(..., description="UUID do serviço a ser agendado")
    data_agendamento: datetime = Field(..., description="Data e hora de início do agendamento (UTC)")
    cliente_nome: str = Field(..., min_length=2, max_length=200, description="Nome do cliente")
    cliente_contato: str = Field(..., min_length=10, max_length=20, description="Contato (telefone ou e-mail) do cliente")
    
    @field_validator('cliente_contato')
    @classmethod
    def validate_contact(cls, v: str) -> str:
        """Valida e normaliza o contato (telefone ou e-mail)."""
        # Se for telefone, remove caracteres não numéricos
        if any(c.isdigit() for c in v):
            phone_clean = ''.join(filter(str.isdigit, v))
            if len(phone_clean) < 10:
                raise ValueError("Telefone deve conter pelo menos 10 dígitos")
            return phone_clean
        # Se for e-mail, valida formato básico
        if '@' not in v:
            raise ValueError("E-mail inválido ou telefone deve conter pelo menos 10 dígitos")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_id": "123e4567-e89b-12d3-a456-426614174000",
                "data_agendamento": "2024-01-15T10:00:00Z",
                "cliente_nome": "João Silva",
                "cliente_contato": "11987654321"
            }
        }


class AppointmentCancelRequest(BaseModel):
    """Schema para requisição de cancelamento de agendamento."""
    cancellation_reason: str = Field(..., min_length=3, max_length=500, description="Motivo do cancelamento (obrigatório)")


class AppointmentResponse(BaseModel):
    """Schema de resposta para Appointment."""
    id: UUID
    tenant_id: UUID
    service_id: Optional[UUID] = None  # Nullable para bloqueios
    service_name: Optional[str] = None  # Nome do serviço (para exibição)
    service_display_color_code: Optional[str] = None  # Cor de exibição do serviço na agenda
    customer_name: Optional[str] = None  # Nullable para bloqueios
    customer_phone: Optional[str] = None  # Nullable para bloqueios
    start_datetime: datetime
    end_datetime: datetime
    status: str
    is_manual_block: Optional[bool] = False  # True para bloqueios manuais
    description: Optional[str] = None  # Descrição do bloqueio
    cancellation_reason: Optional[str] = None  # Motivo do cancelamento
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "service_id": "123e4567-e89b-12d3-a456-426614174002",
                "customer_name": "Maria Silva",
                "customer_phone": "11987654321",
                "start_datetime": "2024-01-15T10:00:00Z",
                "end_datetime": "2024-01-15T10:45:00Z",
                "status": "PENDING",
                "created_at": "2024-01-14T15:30:00Z",
                "updated_at": "2024-01-14T15:30:00Z"
            }
        }

