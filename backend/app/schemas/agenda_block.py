"""
Schemas Pydantic para bloqueio de agenda (Manual Blocks).
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class AgendaBlockCreate(BaseModel):
    """Schema para criação de um bloqueio de agenda."""
    start_datetime: datetime = Field(..., description="Data e hora de início do bloqueio (UTC)")
    end_datetime: datetime = Field(..., description="Data e hora de fim do bloqueio (UTC)")
    description: str = Field(..., min_length=3, max_length=500, description="Descrição do bloqueio (ex: 'Almoço Prolongado', 'Folga', 'Manutenção')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_datetime": "2024-01-15T12:00:00Z",
                "end_datetime": "2024-01-15T13:30:00Z",
                "description": "Almoço Prolongado"
            }
        }


class AgendaBlockResponse(BaseModel):
    """Schema de resposta para bloqueio de agenda."""
    id: UUID
    tenant_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    description: Optional[str]
    is_manual_block: bool
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "start_datetime": "2024-01-15T12:00:00Z",
                "end_datetime": "2024-01-15T13:30:00Z",
                "description": "Almoço Prolongado",
                "is_manual_block": True,
                "status": "CONFIRMED",
                "created_at": "2024-01-14T15:30:00Z",
                "updated_at": "2024-01-14T15:30:00Z"
            }
        }


