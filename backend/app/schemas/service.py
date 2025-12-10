"""
Schemas Pydantic para a entidade Service (Serviço).
"""
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional
from datetime import datetime


class ServiceBase(BaseModel):
    """Schema base para Service."""
    name: str = Field(..., min_length=2, max_length=200, description="Nome do serviço")
    duration_minutes: int = Field(..., gt=0, le=480, description="Duração do serviço em minutos (máximo 8 horas)")
    price: Decimal = Field(..., ge=0, decimal_places=2, description="Preço do serviço")
    fixed_cost_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Custo fixo do serviço (para cálculo de lucro)")
    
    # Campos de promoção
    is_promotional: Optional[bool] = Field(False, description="Se o serviço está em promoção")
    promotion_start_date: Optional[datetime] = Field(None, description="Data/hora de início da promoção (UTC)")
    promotion_end_date: Optional[datetime] = Field(None, description="Data/hora de fim da promoção (UTC)")
    promotional_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Valor promocional do serviço")
    promotion_display_name: Optional[str] = Field(None, max_length=200, description="Nome da promoção (ex: 'Promoção de Natal')")
    promotion_description: Optional[str] = Field(None, description="Descrição/observação da promoção")
    promotion_color_code: Optional[str] = Field(None, max_length=7, description="Código hex da cor da promoção (ex: '#FF0000')")
    
    # Campos de exibição e descrição
    display_color_code: Optional[str] = Field(None, max_length=7, description="Cor de exibição na Agenda Admin (ex: '#4A90E2')")
    long_description: Optional[str] = Field(None, description="Descrição detalhada do serviço")


class ServiceCreate(ServiceBase):
    """Schema para criação de um novo Service."""
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Corte de Cabelo",
                "duration_minutes": 45,
                "price": "50.00"
            }
        }


class ServiceUpdate(BaseModel):
    """Schema para atualização parcial de Service."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    fixed_cost_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    # Campos de promoção
    is_promotional: Optional[bool] = None
    promotion_start_date: Optional[datetime] = None
    promotion_end_date: Optional[datetime] = None
    promotional_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    promotion_display_name: Optional[str] = Field(None, max_length=200)
    promotion_description: Optional[str] = None
    promotion_color_code: Optional[str] = Field(None, max_length=7)
    
    # Campos de exibição e descrição
    display_color_code: Optional[str] = Field(None, max_length=7, description="Cor de exibição na Agenda Admin")
    long_description: Optional[str] = Field(None, description="Descrição detalhada do serviço")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Corte de Cabelo Premium",
                "duration_minutes": 60,
                "price": "75.00"
            }
        }


class ServiceResponse(ServiceBase):
    """Schema de resposta para Service."""
    id: UUID
    tenant_id: UUID
    fixed_cost_value: Optional[Decimal] = None
    
    # Campos de promoção (incluídos do ServiceBase)
    is_promotional: bool = False
    promotion_start_date: Optional[datetime] = None
    promotion_end_date: Optional[datetime] = None
    promotional_value: Optional[Decimal] = None
    promotion_display_name: Optional[str] = None
    promotion_description: Optional[str] = None
    promotion_color_code: Optional[str] = None
    
    # Campos de exibição e descrição
    display_color_code: Optional[str] = None
    long_description: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "Corte de Cabelo",
                "duration_minutes": 45,
                "price": "50.00"
            }
        }


