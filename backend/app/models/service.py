"""
Modelo SQLAlchemy para a entidade Service (Serviço/Catálogo).
"""
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DECIMAL, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base


class Service(Base):
    """
    Modelo Service representa um serviço oferecido pelo estúdio.
    Ex: "Corte de Cabelo", "Manicure", etc.
    """
    __tablename__ = "services"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # Duração em minutos
    price = Column(DECIMAL(10, 2), nullable=False)  # Preço em decimal
    fixed_cost_value = Column(DECIMAL(10, 2), nullable=True)  # Custo fixo do serviço (para cálculo de lucro)
    
    # Campos de promoção
    is_promotional = Column(Boolean, default=False, nullable=False, index=True)
    promotion_start_date = Column(DateTime, nullable=True)  # UTC
    promotion_end_date = Column(DateTime, nullable=True)  # UTC
    promotional_value = Column(DECIMAL(10, 2), nullable=True)  # Valor promocional
    promotion_display_name = Column(String(200), nullable=True)  # Ex: "Promoção de Natal"
    promotion_description = Column(Text, nullable=True)  # Observação/descrição da promoção
    promotion_color_code = Column(String(7), nullable=True)  # Código hex da cor (ex: "#FF0000")
    
    # Campos de exibição e descrição
    display_color_code = Column(String(7), nullable=True)  # Cor de exibição na Agenda Admin (ex: "#4A90E2")
    long_description = Column(Text, nullable=True)  # Descrição detalhada do serviço
    
    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.name}', duration={self.duration_minutes}min)>"


