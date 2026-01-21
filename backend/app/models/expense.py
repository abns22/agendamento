"""
Modelo SQLAlchemy para a entidade Expense (Despesa).
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, DECIMAL, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ENUM as PostgreSQLEnum
import enum
import uuid
from datetime import datetime
from app.core.database import Base


class PaymentMethodEnum(str, enum.Enum):
    """Enum para métodos de pagamento de despesas."""
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    PIX = "PIX"
    BANK_TRANSFER = "BANK_TRANSFER"


class Expense(Base):
    """
    Modelo Expense representa uma despesa operacional do estúdio.
    Ex: Aluguel, Material, Salário, etc.
    """
    __tablename__ = "expenses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)  # Descrição da despesa (Ex: "Conta de Luz")
    item_name = Column(String(200), nullable=True)  # Nome do item comprado (opcional)
    amount = Column(DECIMAL(10, 2), nullable=False)  # Valor da despesa
    # Para PostgreSQL: usar o tipo ENUM existente 'payment_method_enum'
    # O tipo já foi criado na migração com CREATE TYPE payment_method_enum
    payment_method = Column(
        PostgreSQLEnum(PaymentMethodEnum, name='payment_method_enum', create_type=False),
        nullable=False,
        index=True
    )  # Método de pagamento
    payment_date = Column(DateTime, nullable=False, index=True)  # Data em que o dinheiro saiu do caixa
    category = Column(String(100), nullable=True)  # Categoria (ex: 'FIXO', 'VARIAVEL')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Expense(id={self.id}, tenant_id={self.tenant_id}, amount={self.amount}, payment_method='{self.payment_method}')>"

