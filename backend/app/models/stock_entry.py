"""
Modelo StockEntry - Entradas de estoque para controle físico do inventário.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum as SQLEnum
from app.core.database import Base
import enum


class UnitType(str, enum.Enum):
    """Tipos de unidade para estoque."""
    UNITARIO = "UNITARIO"  # Unidade individual
    PACOTE = "PACOTE"      # Pacote (ex: 10 unidades)
    CAIXA = "CAIXA"        # Caixa (ex: 50 unidades)


class StockEntry(Base):
    """
    Modelo para gerenciar o inventário físico de produtos.
    """
    __tablename__ = "stock_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    unit_type = Column(SQLEnum(UnitType), nullable=False, default=UnitType.UNITARIO)
    quantity = Column(Integer, nullable=False, default=0)  # Quantidade atual em estoque
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<StockEntry(id={self.id}, product_id={self.product_id}, unit_type={self.unit_type}, quantity={self.quantity})>"

