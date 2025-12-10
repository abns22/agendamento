"""
Modelo SQLAlchemy para a entidade Tenant (Empresa).
"""
from sqlalchemy import Column, String, Boolean, Text
import uuid
from app.core.database import Base


class Tenant(Base):
    """
    Modelo Tenant representa uma empresa/estúdio que usa o sistema.
    Cada tenant tem seus próprios dados isolados.
    """
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    whatsapp_phone_id = Column(String(50), nullable=True)  # ID do número WhatsApp Business na Meta API
    notification_phone_number = Column(String(20), nullable=True)  # Número do estúdio para receber notificações (formato internacional)
    stripe_subscription_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Campos públicos para personalização da página de agendamento
    name = Column(String(200), nullable=True)  # Nome do estúdio (ex: "Estúdio Bella")
    logo_url = Column(String(500), nullable=True)  # URL da logo do estúdio
    description = Column(Text, nullable=True)  # Breve descrição do estúdio
    address = Column(Text, nullable=True)  # Endereço físico do estúdio
    phone_contact = Column(String(20), nullable=True)  # Número de telefone público para contato
    schedule_display_text = Column(String(200), nullable=True)  # Texto amigável do horário (ex: "Segunda a Sexta, 09:00 - 18:00")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, slug='{self.slug}', name='{self.name}', is_active={self.is_active})>"


