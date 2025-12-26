"""
Modelo SQLAlchemy para a tabela intermediária AppointmentService (relação Many-to-Many).
"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class AppointmentService(Base):
    """
    Tabela intermediária para relação Many-to-Many entre Appointments e Services.
    Permite que um agendamento tenha múltiplos serviços.
    """
    __tablename__ = "appointment_services"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(String(36), ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    
    def __repr__(self):
        return f"<AppointmentService(appointment_id={self.appointment_id}, service_id={self.service_id})>"

