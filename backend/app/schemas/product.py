"""
Schemas Pydantic para Product.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from decimal import Decimal


class ProductBase(BaseModel):
    """Schema base para Product."""
    name: str = Field(..., min_length=1, max_length=200, description="Nome do produto")
    category_id: Optional[UUID] = Field(None, description="ID da categoria do produto")
    unit_cost: Decimal = Field(..., ge=0, decimal_places=2, description="Custo unitário de aquisição")


class ProductCreate(ProductBase):
    """Schema para criação de produto."""
    pass


class ProductUpdate(BaseModel):
    """Schema para atualização de produto."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Nome do produto")
    category_id: Optional[UUID] = Field(None, description="ID da categoria do produto")
    unit_cost: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Custo unitário de aquisição")


class ProductResponse(ProductBase):
    """Schema de resposta para Product."""
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

