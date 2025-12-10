"""
Modelo SQLAlchemy para a entidade PaymentInstallmentConfig (Configuração de Taxas de Parcelamento).
"""
from sqlalchemy import Column, String, ForeignKey, Integer, DECIMAL
import uuid
import enum
from app.core.database import Base


class TaxType(str, enum.Enum):
    """Tipo de taxa: percentual ou valor fixo."""
    PERCENT = "%"
    FIXED = "R$"


class PaymentInstallmentConfig(Base):
    """
    Modelo PaymentInstallmentConfig representa as taxas de parcelamento para Cartão de Crédito.
    Ex: 2x com 2%, 3x com 3%, etc.
    """
    __tablename__ = "payment_installment_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    payment_method_id = Column(String(36), ForeignKey("payment_method_configs.id"), nullable=False, index=True)
    installments_count = Column(Integer, nullable=False)  # Número de parcelas (2, 3, 4, etc.)
    tax_type = Column(String(10), nullable=False)  # '%' ou 'R$' - usando String diretamente para evitar problemas com enum
    tax_value = Column(DECIMAL(10, 2), nullable=False)  # Valor da taxa
    
    def __repr__(self):
        return f"<PaymentInstallmentConfig(id={self.id}, installments={self.installments_count}x, tax={self.tax_value}{self.tax_type})>"

