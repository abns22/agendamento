"""
Schemas Pydantic para endpoints públicos de agendamento.
"""
from pydantic import BaseModel, Field
from typing import List
from uuid import UUID


class AvailableSlotsResponse(BaseModel):
    """Schema de resposta para horários disponíveis."""
    tenant_slug: str = Field(..., description="Slug do tenant")
    service_id: UUID = Field(..., description="ID do serviço")
    date: str = Field(..., description="Data no formato YYYY-MM-DD")
    available_slots: List[str] = Field(..., description="Lista de horários disponíveis no formato HH:MM")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_slug": "estudio-bella",
                "service_id": "123e4567-e89b-12d3-a456-426614174000",
                "date": "2024-01-15",
                "available_slots": ["09:00", "09:15", "09:30", "10:00", "10:30"]
            }
        }


