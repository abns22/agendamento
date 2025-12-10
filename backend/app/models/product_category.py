"""
Modelo ProductCategory - Categorias de produtos para organização do inventário.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from app.core.database import Base


class ProductCategory(Base):
    """
    Modelo para categorizar produtos do inventário.
    """
    __tablename__ = "product_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProductCategory(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"

