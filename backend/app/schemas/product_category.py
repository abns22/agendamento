"""
Schemas Pydantic para ProductCategory.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class ProductCategoryBase(BaseModel):
    """Schema base para ProductCategory."""
    name: str = Field(..., min_length=1, max_length=200, description="Nome da categoria")


class ProductCategoryCreate(ProductCategoryBase):
    """Schema para criação de categoria."""
    pass


class ProductCategoryUpdate(BaseModel):
    """Schema para atualização de categoria."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Nome da categoria")


class ProductCategoryResponse(ProductCategoryBase):
    """Schema de resposta para ProductCategory."""
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

