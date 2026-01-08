"""
Schemas Pydantic para a entidade Appointment (Agendamento).
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal


class AppointmentCreate(BaseModel):
    """Schema para criação de um novo agendamento."""
    service_ids: Optional[List[UUID]] = Field(None, min_length=1, description="Lista de UUIDs dos serviços a serem agendados")
    customer_name: str = Field(..., min_length=2, max_length=200, description="Nome do cliente")
    customer_phone: str = Field(..., min_length=10, max_length=20, description="Telefone do cliente")
    start_datetime: datetime = Field(..., description="Data e hora de início do agendamento (UTC)")
    
    # Compatibilidade retroativa: aceitar service_id único também
    service_id: Optional[UUID] = Field(None, description="DEPRECATED: Use service_ids. UUID único do serviço (para compatibilidade)")
    
    @field_validator('customer_phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Valida e normaliza o telefone."""
        # Remove caracteres não numéricos
        phone_clean = ''.join(filter(str.isdigit, v))
        if len(phone_clean) < 10:
            raise ValueError("Telefone deve conter pelo menos 10 dígitos")
        return phone_clean
    
    @model_validator(mode='after')
    def normalize_service_ids(self):
        """Normaliza service_ids: se service_id único for fornecido, converte para lista."""
        # Se service_ids não foi fornecido mas service_id foi, usar service_id
        if not self.service_ids and self.service_id:
            self.service_ids = [self.service_id]
        # Validar que pelo menos um serviço foi fornecido
        if not self.service_ids:
            raise ValueError("É necessário fornecer service_ids ou service_id")
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "customer_name": "Maria Silva",
                "customer_phone": "11987654321",
                "start_datetime": "2024-01-15T10:00:00Z"
            }
        }


class ManualAppointmentCreate(BaseModel):
    """Schema para criação de agendamento manual pelo administrador."""
    service_ids: Optional[List[UUID]] = Field(None, min_length=1, description="Lista de UUIDs dos serviços a serem agendados")
    data_agendamento: datetime = Field(..., description="Data e hora de início do agendamento (UTC)")
    client_id: Optional[UUID] = Field(None, description="ID do cliente (opcional, se não fornecido será criado/buscado pelo telefone)")
    cliente_nome: str = Field(..., min_length=2, max_length=200, description="Nome do cliente")
    cliente_contato: str = Field(..., min_length=10, max_length=20, description="Contato (telefone ou e-mail) do cliente")
    cliente_aniversario: Optional[date] = Field(None, description="Data de nascimento do cliente (opcional)")
    
    # Compatibilidade retroativa: aceitar service_id único também
    service_id: Optional[UUID] = Field(None, description="DEPRECATED: Use service_ids. UUID único do serviço (para compatibilidade)")
    
    @field_validator('cliente_aniversario', mode='before')
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
    
    @model_validator(mode='after')
    def normalize_service_ids(self):
        """Normaliza service_ids: se service_id único for fornecido, converte para lista."""
        # Se service_ids não foi fornecido mas service_id foi, usar service_id
        if not self.service_ids and self.service_id:
            self.service_ids = [self.service_id]
        # Validar que pelo menos um serviço foi fornecido
        if not self.service_ids:
            raise ValueError("É necessário fornecer service_ids ou service_id")
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "data_agendamento": "2024-01-15T10:00:00Z",
                "cliente_nome": "João Silva",
                "cliente_contato": "11987654321"
            }
        }


class AppointmentCancelRequest(BaseModel):
    """Schema para requisição de cancelamento de agendamento."""
    cancellation_reason: str = Field(..., min_length=3, max_length=500, description="Motivo do cancelamento (obrigatório)")


class AppointmentRescheduleRequest(BaseModel):
    """Schema para reagendamento de um agendamento existente."""
    data_agendamento: datetime = Field(..., description="Nova data e hora de início do agendamento (UTC)")
    service_ids: Optional[List[UUID]] = Field(
        None,
        min_length=1,
        description="Nova lista de UUIDs dos serviços (opcional, usa os atuais se não for enviado)"
    )
    # Compatibilidade retroativa
    service_id: Optional[UUID] = Field(
        None,
        description="DEPRECATED: Use service_ids. Novo UUID único do serviço (opcional, para compatibilidade)"
    )
    
    @model_validator(mode='after')
    def normalize_service_ids(self):
        """Normaliza service_ids: se service_id único for fornecido, converte para lista."""
        if not self.service_ids and self.service_id:
            self.service_ids = [self.service_id]
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "data_agendamento": "2024-01-20T14:00:00Z",
                "service_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class AppointmentUpdate(BaseModel):
    """Schema para atualização de um agendamento existente."""
    status: Optional[str] = Field(default=None, description="Novo status do agendamento (PENDING, CONFIRMED, CANCELED, COMPLETED)")
    start_datetime: Optional[datetime] = Field(default=None, description="Nova data e hora de início do agendamento (UTC)")
    service_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Nova lista de UUIDs dos serviços (opcional, mantém os atuais se não for enviado)"
    )
    # Compatibilidade retroativa
    service_id: Optional[UUID] = Field(
        default=None,
        description="DEPRECATED: Use service_ids. Novo UUID único do serviço (opcional, para compatibilidade)"
    )
    
    @model_validator(mode='after')
    def normalize_service_ids(self):
        """Normaliza service_ids: se service_id único for fornecido, converte para lista."""
        # Garantir que service_ids sempre existe (mesmo que seja None)
        if not hasattr(self, 'service_ids') or self.service_ids is None:
            self.service_ids = None
        
        # Se service_ids não foi fornecido mas service_id foi, converter para lista
        if (not self.service_ids or len(self.service_ids) == 0) and self.service_id:
            self.service_ids = [self.service_id]
        
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "status": "CONFIRMED",
                "start_datetime": "2024-01-20T14:00:00Z",
                "service_ids": ["123e4567-e89b-12d3-a456-426614174000"]
            }
        }


class AppointmentResponse(BaseModel):
    """Schema de resposta para Appointment."""
    id: UUID
    tenant_id: UUID
    service_id: Optional[UUID] = None  # DEPRECATED: Use services. Mantido para compatibilidade
    service_ids: Optional[List[UUID]] = None  # Lista de UUIDs dos serviços
    service_name: Optional[str] = None  # Nome do primeiro serviço (para compatibilidade, DEPRECATED)
    service_names: Optional[List[str]] = None  # Lista de nomes dos serviços
    service_display_color_code: Optional[str] = None  # Cor do primeiro serviço (para compatibilidade)
    service_display_color_codes: Optional[List[str]] = None  # Lista de cores dos serviços
    total_value: Optional[Decimal] = None  # Valor total agendado (soma dos serviços com promoções)
    client_id: Optional[UUID] = None  # ID do cliente (CRM) - opcional
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

