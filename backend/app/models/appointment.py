"""
Modelo SQLAlchemy para a entidade Appointment (Agendamento).
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Boolean, Text, DECIMAL
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from app.core.database import Base


class AppointmentStatus(str, enum.Enum):
    """Status possíveis de um agendamento."""
    SCHEDULED = "SCHEDULED"  # Agendado (padrão)
    PENDING = "PENDING"  # Pendente (compatibilidade)
    CONFIRMED = "CONFIRMED"  # Confirmado (compatibilidade)
    COMPLETED = "COMPLETED"  # Finalizado/Concluído
    CANCELED = "CANCELED"  # Cancelado


class Appointment(Base):
    """
    Modelo Appointment representa um agendamento de serviço.
    """
    __tablename__ = "appointments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    service_id = Column(String(36), ForeignKey("services.id"), nullable=True, index=True)  # Nullable para bloqueios
    customer_name = Column(String(200), nullable=True)  # Nullable para bloqueios
    customer_phone = Column(String(20), nullable=True)  # Nullable para bloqueios
    start_datetime = Column(DateTime, nullable=False, index=True)  # UTC (MySQL não suporta timezone=True)
    end_datetime = Column(DateTime, nullable=False)  # UTC
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False, index=True)
    is_manual_block = Column(Boolean, default=False, nullable=False, index=True)  # True para bloqueios manuais
    description = Column(Text, nullable=True)  # Descrição do bloqueio (ex: "Almoço Prolongado")
    cancellation_reason = Column(Text, nullable=True)  # Motivo do cancelamento (quando status = CANCELED)
    # Campos de histórico financeiro (após finalização)
    final_sale_value = Column(DECIMAL(10, 2), nullable=True)  # Valor final de venda (para histórico)
    service_cost = Column(DECIMAL(10, 2), nullable=True)  # Custo do serviço (para histórico)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, tenant_id={self.tenant_id}, {self.start_datetime} - {self.status})>"

