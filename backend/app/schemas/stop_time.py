"""
Schemas Pydantic para validação de entrada/saída da entidade StopTime.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import time


class StopTimeBase(BaseModel):
    """Schema base para StopTime."""
    day_of_week: int = Field(..., ge=0, le=6, description="Dia da semana (0=Segunda, 6=Domingo)")
    start_time: time = Field(..., description="Horário de início da parada (ex: 12:00)")
    end_time: time = Field(..., description="Horário de fim da parada (ex: 13:00)")
    description: Optional[str] = Field(None, max_length=200, description="Descrição opcional (ex: 'Almoço', 'Pausa')")


class StopTimeCreate(StopTimeBase):
    """Schema para criação de StopTime."""
    pass


class StopTimeUpdate(BaseModel):
    """Schema para atualização de StopTime."""
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Dia da semana (0=Segunda, 6=Domingo)")
    start_time: Optional[time] = Field(None, description="Horário de início da parada")
    end_time: Optional[time] = Field(None, description="Horário de fim da parada")
    description: Optional[str] = Field(None, max_length=200, description="Descrição opcional")


class StopTimeResponse(StopTimeBase):
    """Schema de resposta para StopTime."""
    id: UUID
    tenant_id: UUID

    class Config:
        from_attributes = True

