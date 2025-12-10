"""
Modelo SQLAlchemy para a entidade PaymentMethodConfig (Configuração de Forma de Pagamento).
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DECIMAL
import uuid
from app.core.database import Base


class PaymentMethodConfig(Base):
    """
    Modelo PaymentMethodConfig representa as configurações de formas de pagamento por Tenant.
    Ex: 'Dinheiro', 'Pix', 'Cartão de Débito', 'Cartão de Crédito'
    """
    __tablename__ = "payment_method_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    method_name = Column(String(100), nullable=False)  # Ex: 'Credit Card', 'Debit Card', 'Pix', 'Cash'
    is_editable = Column(Boolean, default=True, nullable=False)  # False para 'Dinheiro' e 'Pix' (padrões)
    max_installments = Column(Integer, nullable=True)  # Máximo de parcelas (apenas para crédito)
    # Taxa base para débito (em % ou R$)
    debit_tax_type = Column(String(10), nullable=True)  # '%' ou 'R$'
    debit_tax_value = Column(DECIMAL(10, 2), nullable=True)  # Valor da taxa de débito
    
    def __repr__(self):
        return f"<PaymentMethodConfig(id={self.id}, tenant_id={self.tenant_id}, method='{self.method_name}')>"

