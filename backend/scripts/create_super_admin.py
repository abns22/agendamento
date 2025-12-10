"""
Script para criar o primeiro usuário Super Admin.

Este script cria:
1. Um tenant especial para o super admin (ou usa um existente)
2. Um usuário com role SUPER_ADMIN

Uso:
    python scripts/create_super_admin.py
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
        print(f"✅ Arquivo .env carregado: {env_path}")
    else:
        print(f"⚠️  Arquivo .env não encontrado em: {env_path}")
except ImportError:
    print("⚠️  python-dotenv não instalado. Usando variáveis de ambiente do sistema...")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.core.database import Base
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole

# Debug: Verificar se DATABASE_URL foi carregado
import os
env_db_url = os.getenv("DATABASE_URL")
if env_db_url:
    print(f"📊 DATABASE_URL do .env: {env_db_url.split('@')[0]}@***")
else:
    print("⚠️  DATABASE_URL não encontrado no .env")


async def create_super_admin():
    """
    Cria o usuário Super Admin.
    """
    # Obter DATABASE_URL - tentar do .env primeiro, depois do settings
    database_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    
    if not database_url or "user:password" in database_url:
        print("❌ DATABASE_URL não configurado corretamente no .env")
        print()
        print("Por favor, verifique o arquivo .env na pasta backend/")
        print("Ele deve conter uma linha como:")
        print("DATABASE_URL=mysql+aiomysql://root:SUA_SENHA@localhost:3306/agendamento_db")
        print()
        return
    
    print(f"📊 Usando DATABASE_URL: {database_url.split('@')[0]}@***")  # Não mostrar senha
    print()
    
    # Criar engine
    try:
        engine = create_async_engine(
            database_url,
            echo=False  # Desabilitar echo para não poluir a saída
        )
    except Exception as e:
        print(f"❌ Erro ao criar engine: {str(e)}")
        print()
        print("⚠️  Se o erro persistir, use o script alternativo:")
        print("   python scripts/criar_super_admin_simples.py")
        print("   Ele gera o SQL para você executar manualmente no MySQL Workbench.")
        raise
    
    # Criar session factory
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
        
        # Solicitar dados do Super Admin
        print("Por favor, informe os dados do Super Admin:")
        print()
        
        email = input("Email do Super Admin: ").strip()
        if not email:
            print("❌ Email é obrigatório!")
            return
        
        password = input("Senha do Super Admin (mínimo 8 caracteres): ").strip()
        if len(password) < 8:
            print("❌ Senha deve ter no mínimo 8 caracteres!")
            return
        
        confirm_password = input("Confirme a senha: ").strip()
        if password != confirm_password:
            print("❌ As senhas não coincidem!")
            return
        
        print()
        print("Verificando se o email já existe...")
        
        # Verificar se o email já existe
        existing_user = await db.execute(
            select(User).where(User.email == email)
        )
        if existing_user.scalar_one_or_none():
            print(f"❌ Email '{email}' já está em uso!")
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


if __name__ == "__main__":
    try:
        asyncio.run(create_super_admin())
    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao criar Super Admin: {str(e)}")
        import traceback
        traceback.print_exc()

