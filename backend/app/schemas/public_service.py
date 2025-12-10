"""
Schemas Pydantic para serviços públicos (com validação de promoções).
"""
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional
from datetime import datetime


class PublicServiceResponse(BaseModel):
    """
    Schema de resposta para serviços públicos.
    Inclui validação de promoção ativa.
    """
    id: UUID
    name: str
    duration_minutes: int
    price: Decimal  # Preço original
    effective_price: Decimal  # Preço efetivo (promocional se ativo, senão original)
    
    # Dados de promoção (apenas se ativa)
    is_promotional: bool = False
    promotion_active: bool = False  # Se a promoção está ativa no momento
    promotional_value: Optional[Decimal] = None
    promotion_display_name: Optional[str] = None
    promotion_description: Optional[str] = None
    promotion_color_code: Optional[str] = None
    promotion_start_date: Optional[datetime] = None
    promotion_end_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

