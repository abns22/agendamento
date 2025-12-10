"""
Modelo SQLAlchemy para a entidade Debtor (Devedor/Conta a Receber).
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, DECIMAL, Enum as SQLEnum
import uuid
import enum
from datetime import datetime
from app.core.database import Base


class DebtorStatus(str, enum.Enum):
    """Status possíveis de um devedor."""
    PENDING = "PENDING"  # Pendente (não pago)
    PAID = "PAID"  # Pago


class Debtor(Base):
    """
    Modelo Debtor representa uma conta a receber (venda a prazo).
    Vinculado a uma Transaction que foi criada com is_paid=False.
    """
    __tablename__ = "debtors"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    client_name = Column(String(200), nullable=False)  # Nome do cliente devedor
    client_phone = Column(String(20), nullable=True)  # Telefone do cliente
    due_date = Column(DateTime, nullable=False, index=True)  # Data de vencimento (UTC)
    value_due = Column(DECIMAL(10, 2), nullable=False)  # Valor devido (net_value da transaction)
    status = Column(SQLEnum(DebtorStatus), default=DebtorStatus.PENDING, nullable=False, index=True)
    paid_at = Column(DateTime, nullable=True)  # Data/hora do pagamento (quando status = PAID)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Debtor(id={self.id}, transaction_id={self.transaction_id}, client_name='{self.client_name}', status={self.status})>"

