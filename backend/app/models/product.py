"""
Modelo Product - Produtos do inventário interno do estúdio.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, DECIMAL
from app.core.database import Base


class Product(Base):
    """
    Modelo para produtos do inventário interno.
    Focado apenas em controle de custo, sem venda ao cliente.
    """
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("product_categories.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    unit_cost = Column(DECIMAL(10, 2), nullable=False, default=0.00)  # Custo de aquisição
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', tenant_id={self.tenant_id}, unit_cost={self.unit_cost})>"

