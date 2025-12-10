"""
Modelo SQLAlchemy para a entidade ScheduleConfig (Configuração de Horários de Funcionamento).
"""
from sqlalchemy import Column, String, Integer, Time, Boolean, ForeignKey, UniqueConstraint
import uuid
from app.core.database import Base


class ScheduleConfig(Base):
    """
    Modelo ScheduleConfig representa os horários de funcionamento do estúdio.
    Um registro para cada dia da semana (0=Segunda, 6=Domingo).
    """
    __tablename__ = "schedule_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Segunda, 1=Terça, ..., 6=Domingo
    start_time = Column(Time, nullable=False)  # Horário de abertura (ex: 09:00)
    end_time = Column(Time, nullable=False)  # Horário de fechamento (ex: 18:00)
    is_closed = Column(Boolean, default=False, nullable=False)  # Se o dia está fechado
    
    # Constraint: um tenant não pode ter duas configurações para o mesmo dia
    __table_args__ = (
        UniqueConstraint('tenant_id', 'day_of_week', name='uq_tenant_day'),
    )
    
    def __repr__(self):
        return f"<ScheduleConfig(tenant_id={self.tenant_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})>"


