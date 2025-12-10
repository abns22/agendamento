"""
Script para criar o Super Admin automaticamente.
Cria o super admin com as credenciais: alfredo_gi@hotmail.com / 12031994@lF
"""
import asyncio
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Carregar .env ANTES de importar settings
try:
    from dotenv import load_dotenv
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole


async def create_super_admin_auto():
    """Cria o super admin automaticamente."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as db:
        print("=" * 60)
        print("CRIAÇÃO AUTOMÁTICA DE SUPER ADMIN")
        print("=" * 60)
        print()
        
        email = "alfredo_gi@hotmail.com"
        password = "12031994@lF"
        
        print(f"📧 Email: {email}")
        print("🔐 Senha: ********")
        print()
        
        # Verificar se o email já existe
        print("Verificando se o email já existe...")
        existing_user = await db.execute(
            select(User).where(User.email == email)
        )
        user = existing_user.scalar_one_or_none()
        
        if user:
            print(f"✅ Usuário '{email}' já existe!")
            print(f"   Role atual: {user.role.value}")
            
            # Verificar se já é SUPER_ADMIN
            if user.role == UserRole.SUPER_ADMIN:
                print("✅ Usuário já é SUPER_ADMIN. Nada a fazer!")
                return
            else:
                # Atualizar para SUPER_ADMIN
                print("🔄 Atualizando role para SUPER_ADMIN...")
                user.role = UserRole.SUPER_ADMIN
                user.password_hash = get_password_hash(password)
                await db.commit()
                await db.refresh(user)
                print("✅ Usuário atualizado para SUPER_ADMIN!")
                return
        
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
        print("DADOS DO SUPER ADMIN")
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
        print("   Você pode fazer login com:")
        print(f"   Email: {email}")
        print(f"   Senha: {password}")
        print()
    
    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(create_super_admin_auto())
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

