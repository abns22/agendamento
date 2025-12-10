"""
Modelo SQLAlchemy para a entidade User (Usuário/Administrador).
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from app.core.database import Base


class UserRole(str, enum.Enum):
    """Roles possíveis de um usuário."""
    SUPER_ADMIN = "SUPER_ADMIN"  # Super administrador (acesso global)
    TENANT_ADMIN = "TENANT_ADMIN"  # Administrador do estúdio (tenant específico)
    ADMIN = "ADMIN"  # Alias para TENANT_ADMIN (compatibilidade)
    STAFF = "STAFF"  # Funcionário/Staff (futuro)


class User(Base):
    """
    Modelo User representa um usuário/administrador do sistema.
    Cada usuário pertence a um Tenant (estúdio).
    """
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Hash bcrypt da senha
    role = Column(SQLEnum(UserRole), default=UserRole.TENANT_ADMIN, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tenant_id={self.tenant_id}, role={self.role})>"


