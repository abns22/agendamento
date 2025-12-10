"""
Modelo SQLAlchemy para a entidade StopTime (Intervalos de Parada/Almoço).
"""
from sqlalchemy import Column, String, Integer, Time, ForeignKey, UniqueConstraint
import uuid
from app.core.database import Base


class StopTime(Base):
    """
    Modelo StopTime representa intervalos de parada/almoço por dia da semana.
    Um tenant pode ter múltiplos intervalos de parada no mesmo dia.
    Ex: Almoço das 12:00 às 13:00, Pausa das 15:00 às 15:30
    """
    __tablename__ = "stop_times"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Segunda, 1=Terça, ..., 6=Domingo
    start_time = Column(Time, nullable=False)  # Horário de início da parada (ex: 12:00)
    end_time = Column(Time, nullable=False)  # Horário de fim da parada (ex: 13:00)
    description = Column(String(200), nullable=True)  # Descrição opcional (ex: "Almoço", "Pausa")
    
    def __repr__(self):
        return f"<StopTime(tenant_id={self.tenant_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})>"

