"""
Schemas Pydantic para StockEntry.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.stock_entry import UnitType


class StockEntryBase(BaseModel):
    """Schema base para StockEntry."""
    product_id: UUID = Field(..., description="ID do produto")
    unit_type: UnitType = Field(..., description="Tipo de unidade (UNITARIO, PACOTE, CAIXA)")
    quantity: int = Field(..., ge=0, description="Quantidade em estoque")


class StockEntryCreate(StockEntryBase):
    """Schema para criação de entrada de estoque."""
    pass


class StockEntryUpdate(BaseModel):
    """Schema para atualização de entrada de estoque."""
    unit_type: Optional[UnitType] = Field(None, description="Tipo de unidade")
    quantity: Optional[int] = Field(None, ge=0, description="Quantidade em estoque")


class StockEntryResponse(StockEntryBase):
    """Schema de resposta para StockEntry."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventorySummaryItem(BaseModel):
    """Item do resumo de inventário."""
    product_id: UUID
    product_name: str
    category_name: Optional[str] = None
    unit_cost: Decimal
    total_quantity: int = Field(..., description="Quantidade total em estoque (em unidades)")
    total_value: Decimal = Field(..., description="Valor total de estoque (custo)")


class InventorySummaryResponse(BaseModel):
    """Resumo completo do inventário."""
    items: list[InventorySummaryItem]
    total_products: int
    total_value: Decimal = Field(..., description="Valor total de todo o inventário")

