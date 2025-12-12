"""
Script para criar Super Admin diretamente com email e senha fornecidos.
Uso: python scripts/create_super_admin_direct.py
"""
import asyncio
import sys
import os

# Adicionar o diretório raiz ao path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.tenant import Tenant


def get_database_url():
    """Converte a URL do banco de dados para o formato asyncpg."""
    db_url = settings.DATABASE_URL
    
    if "postgresql+asyncpg://" in db_url:
        return db_url
    if "postgresql://" in db_url:
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "postgres://" in db_url:
        return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    return db_url


async def create_super_admin(email: str, password: str):
    """
    Cria o usuário Super Admin.
    """
    database_url = get_database_url()
    
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as db:
        print("=" * 60)
        print("CRIAÇÃO DE SUPER ADMIN")
        print("=" * 60)
        print()
        
        print(f"Email: {email}")
        print(f"Senha: {'*' * len(password)}")
        print()
        
        # Verificar se o email já existe
        print("Verificando se o email já existe...")
        existing_user = await db.execute(
            select(User).where(User.email == email)
        )
        if existing_user.scalar_one_or_none():
            print(f"❌ Email '{email}' já está em uso!")
            return False
        
        print("✅ Email disponível")
        print()
        
        # Buscar ou criar tenant para o super admin
        print("Buscando tenant para Super Admin...")
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.slug == "super-admin")
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            print("Criando tenant 'super-admin'...")
            tenant = Tenant(
                slug="super-admin",
                is_active=True
            )
            db.add(tenant)
            await db.flush()
            print("✅ Tenant 'super-admin' criado")
        else:
            print("✅ Tenant 'super-admin' já existe")
        
        print()
        print("Gerando hash da senha...")
        
        # Gerar hash da senha
        password_hash = get_password_hash(password)
        
        print("✅ Hash gerado")
        print()
        print("Criando usuário Super Admin...")
        
        # Criar usuário Super Admin
        super_admin = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=password_hash,
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        db.add(super_admin)
        await db.commit()
        await db.refresh(super_admin)
        await db.refresh(tenant)
        
        print("✅ Usuário Super Admin criado com sucesso!")
        print()
        print("=" * 60)
        print("DADOS DO SUPER ADMIN CRIADO")
        print("=" * 60)
        print(f"ID: {super_admin.id}")
        print(f"Email: {super_admin.email}")
        print(f"Role: {super_admin.role.value}")
        print(f"Tenant ID: {super_admin.tenant_id}")
        print(f"Tenant Slug: {tenant.slug}")
        print(f"Ativo: {super_admin.is_active}")
        print("=" * 60)
        print()
        print("✅ Super Admin criado com sucesso!")
        print("   Você pode fazer login com este email e senha.")
        print()
        
        return True


if __name__ == "__main__":
    # Dados do Super Admin
    email = "alfredo_gi@hotmail.com"
    password = "12031994@lF"
    
    try:
        result = asyncio.run(create_super_admin(email, password))
        if result:
            print("✅ Processo concluído com sucesso!")
            sys.exit(0)
        else:
            print("❌ Falha ao criar Super Admin")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

