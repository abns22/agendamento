"""
Modelo SQLAlchemy para a entidade PaymentEntry (Entrada de Pagamento).
"""
from sqlalchemy import Column, String, ForeignKey, Integer, DECIMAL, Boolean
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class PaymentEntry(Base):
    """
    Modelo PaymentEntry representa uma entrada de pagamento dentro de uma transação.
    Permite múltiplas formas de pagamento em uma única transação.
    Ex: R$50 em Dinheiro + R$50 em PIX
    """
    __tablename__ = "payment_entries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    payment_method_id = Column(String(36), ForeignKey("payment_method_configs.id"), nullable=False, index=True)
    value_paid = Column(DECIMAL(10, 2), nullable=False)  # Valor parcial pago nesta forma
    installments = Column(Integer, nullable=True)  # Número de parcelas (apenas para crédito)
    is_bank_account = Column(Boolean, default=False, nullable=False)  # True se for PIX/Cartão (conta bancária)
    
    # Relacionamentos
    transaction = relationship("Transaction", back_populates="payment_entries")
    
    def __repr__(self):
        return f"<PaymentEntry(id={self.id}, transaction_id={self.transaction_id}, value={self.value_paid}, installments={self.installments})>"

