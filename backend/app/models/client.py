"""
Modelo SQLAlchemy para a entidade Client (Cliente).
"""
from sqlalchemy import Column, String, Date, ForeignKey
import uuid
from app.core.database import Base


class Client(Base):
    """
    Modelo Client representa um cliente do estúdio.
    Armazena informações básicas do cliente para CRM e aniversários.
    """
    __tablename__ = "clients"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)  # Número de contato principal
    email = Column(String(200), nullable=True)  # Email opcional
    birth_date = Column(Date, nullable=True, index=True)  # Data de nascimento (fundamental para aniversários)
    
    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', phone='{self.phone_number}')>"

