"""
Modelo SQLAlchemy para a entidade Transaction (Transação/Caixa).
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, DECIMAL, Numeric, Boolean
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base


class Transaction(Base):
    """
    Modelo Transaction representa uma transação de venda no caixa.
    Cada transação está vinculada a um agendamento e registra o valor bruto,
    líquido, custos e lucro.
    """
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=False, index=True)
    date_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)  # Data/hora da transação (UTC)
    gross_value = Column(DECIMAL(10, 2), nullable=False)  # Valor bruto (antes das taxas)
    net_value = Column(DECIMAL(10, 2), nullable=False)  # Valor líquido (após taxas de pagamento)
    total_cost = Column(DECIMAL(10, 2), nullable=False)  # Soma dos fixed_cost_value dos serviços
    total_profit = Column(DECIMAL(10, 2), nullable=False)  # Lucro (net_value - total_cost)
    additional_cost = Column(DECIMAL(10, 2), nullable=True)  # Custo adicional (opcional, para controle interno)
    is_paid = Column(Boolean, default=True, nullable=False, index=True)  # True se foi pago, False se é a prazo
    
    # Relacionamento com PaymentEntry
    payment_entries = relationship("PaymentEntry", back_populates="transaction", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, appointment_id={self.appointment_id}, net_value={self.net_value}, profit={self.total_profit})>"

