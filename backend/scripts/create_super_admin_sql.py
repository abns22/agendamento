"""
Script para criar o Super Admin usando SQL direto.
Usa o hash já gerado anteriormente.
"""
import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Carregar .env
try:
    from dotenv import load_dotenv
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings


async def create_super_admin_sql():
    """Cria o super admin usando SQL direto."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as db:
        print("=" * 60)
        print("CRIAÇÃO DE SUPER ADMIN (SQL)")
        print("=" * 60)
        print()
        
        # Hash já gerado anteriormente para a senha "12031994@lF"
        password_hash = "$2b$12$YT26SIBg9SwXuh.TDHmdF.OY5S8sGgGql3u00t28Fbhqs7ibEMw6y"
        email = "alfredo_gi@hotmail.com"
        
        print(f"📧 Email: {email}")
        print("🔐 Senha: 12031994@lF")
        print()
        
        # Verificar se o usuário já existe
        check_user = await db.execute(
            text("SELECT id, email, role FROM users WHERE email = :email"),
            {"email": email}
        )
        existing = check_user.fetchone()
        
        if existing:
            print(f"✅ Usuário '{email}' já existe!")
            print(f"   Role atual: {existing[2]}")
            
            # Atualizar para SUPER_ADMIN se não for
            if existing[2] != "SUPER_ADMIN":
                print("🔄 Atualizando role para SUPER_ADMIN...")
                await db.execute(
                    text("""
                        UPDATE users 
                        SET role = 'SUPER_ADMIN', 
                            password_hash = :password_hash
                        WHERE email = :email
                    """),
                    {"email": email, "password_hash": password_hash}
                )
                await db.commit()
                print("✅ Usuário atualizado para SUPER_ADMIN!")
            else:
                print("✅ Usuário já é SUPER_ADMIN. Nada a fazer!")
            return
        
        # Criar tenant para super admin (se não existir)
        print("Criando tenant 'super-admin'...")
        await db.execute(
            text("""
                INSERT INTO tenants (id, slug, is_active)
                VALUES (UUID(), 'super-admin', true)
                ON DUPLICATE KEY UPDATE slug = slug
            """)
        )
        await db.commit()
        print("✅ Tenant 'super-admin' criado/verificado")
        print()
        
        # Buscar ID do tenant
        tenant_result = await db.execute(
            text("SELECT id FROM tenants WHERE slug = 'super-admin' LIMIT 1")
        )
        tenant_row = tenant_result.fetchone()
        
        if not tenant_row:
            print("❌ Erro: Não foi possível encontrar o tenant 'super-admin'")
            return
        
        tenant_id = tenant_row[0]
        
        # Criar usuário Super Admin
        print("Criando usuário Super Admin...")
        await db.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, password_hash, role, is_active, created_at, updated_at)
                VALUES (UUID(), :tenant_id, :email, :password_hash, 'SUPER_ADMIN', true, NOW(), NOW())
            """),
            {
                "tenant_id": tenant_id,
                "email": email,
                "password_hash": password_hash
            }
        )
        await db.commit()
        
        # Buscar dados do usuário criado
        user_result = await db.execute(
            text("SELECT id, email, role, is_active FROM users WHERE email = :email"),
            {"email": email}
        )
        user_row = user_result.fetchone()
        
        print("✅ Usuário Super Admin criado com sucesso!")
        print()
        print("=" * 60)
        print("DADOS DO SUPER ADMIN")
        print("=" * 60)
        print(f"ID: {user_row[0]}")
        print(f"Email: {user_row[1]}")
        print(f"Role: {user_row[2]}")
        print(f"Tenant ID: {tenant_id}")
        print(f"Ativo: {bool(user_row[3])}")
        print("=" * 60)
        print()
        print("✅ Super Admin criado com sucesso!")
        print("   Você pode fazer login com:")
        print(f"   Email: {email}")
        print("   Senha: 12031994@lF")
        print()
    
    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(create_super_admin_sql())
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

