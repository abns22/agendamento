"""
Modelo SQLAlchemy para a entidade Expense (Despesa).
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, DECIMAL, Text
import uuid
from datetime import datetime
from app.core.database import Base


class Expense(Base):
    """
    Modelo Expense representa uma despesa operacional do estúdio.
    Ex: Aluguel, Material, Salário, etc.
    """
    __tablename__ = "expenses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)  # Descrição da despesa
    value = Column(DECIMAL(10, 2), nullable=False)  # Valor da despesa
    category = Column(String(100), nullable=True)  # Categoria (ex: Aluguel, Material, Salário)
    date_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)  # Data/hora da despesa (UTC)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Expense(id={self.id}, tenant_id={self.tenant_id}, value={self.value}, category='{self.category}')>"

