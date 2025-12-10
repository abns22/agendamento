"""
Script Python para criar o banco de dados MySQL e todas as tabelas.
Este script não requer o comando 'mysql' no PATH.
"""
import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base

# Importar todos os modelos para que sejam registrados no Base.metadata
from app.models.tenant import Tenant
from app.models.user import User
from app.models.service import Service
from app.models.schedule_config import ScheduleConfig
from app.models.appointment import Appointment


async def create_database():
    """Cria o banco de dados se não existir."""
    # Extrair informações da URL de conexão
    db_url = settings.DATABASE_URL
    
    # Para criar o banco, precisamos conectar sem especificar o banco
    if db_url.startswith("mysql+aiomysql://"):
        # Extrair partes da URL
        parts = db_url.replace("mysql+aiomysql://", "").split("/")
        if len(parts) >= 2:
            credentials = parts[0]
            database_name = parts[1].split("?")[0] if "?" in parts[1] else parts[1]
            
            # URL sem o nome do banco
            base_url = f"mysql+aiomysql://{credentials}/"
            
            print(f"📦 Criando banco de dados: {database_name}")
            
            try:
                engine = create_async_engine(base_url, echo=False)
                async with engine.begin() as conn:
                    # Criar banco de dados
                    await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    print(f"✅ Banco de dados '{database_name}' criado com sucesso!")
                await engine.dispose()
            except Exception as e:
                print(f"❌ Erro ao criar banco de dados: {e}")
                print("\n💡 Dica: Verifique se:")
                print("   - MySQL está rodando")
                print("   - Credenciais no .env estão corretas")
                print("   - Usuário tem permissão para criar bancos")
                return False
    
    return True


async def create_tables():
    """Cria todas as tabelas."""
    print("\n📋 Criando tabelas...")
    
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        async with engine.begin() as conn:
            # Criar todas as tabelas
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Todas as tabelas criadas com sucesso!")
        
        await engine.dispose()
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False


async def insert_test_data():
    """Insere dados de teste."""
    print("\n📝 Inserindo dados de teste...")
    
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        async with engine.begin() as conn:
            # Criar tenant
            tenant_result = await conn.execute(
                text("""
                    INSERT INTO tenants (id, slug, is_active)
                    VALUES (UUID(), 'estudio-bella', true)
                    ON DUPLICATE KEY UPDATE slug = slug
                """)
            )
            
            # Buscar ID do tenant
            tenant_id_result = await conn.execute(
                text("SELECT id FROM tenants WHERE slug = 'estudio-bella' LIMIT 1")
            )
            tenant_row = tenant_id_result.fetchone()
            
            if tenant_row:
                tenant_id = tenant_row[0]
                
                # Criar serviços
                await conn.execute(
                    text("""
                        INSERT INTO services (id, tenant_id, name, duration_minutes, price)
                        SELECT UUID(), :tenant_id, 'Corte de Cabelo', 45, 50.00
                        WHERE NOT EXISTS (
                            SELECT 1 FROM services WHERE tenant_id = :tenant_id AND name = 'Corte de Cabelo'
                        )
                    """),
                    {"tenant_id": tenant_id}
                )
                
                await conn.execute(
                    text("""
                        INSERT INTO services (id, tenant_id, name, duration_minutes, price)
                        SELECT UUID(), :tenant_id, 'Manicure', 60, 35.00
                        WHERE NOT EXISTS (
                            SELECT 1 FROM services WHERE tenant_id = :tenant_id AND name = 'Manicure'
                        )
                    """),
                    {"tenant_id": tenant_id}
                )
                
                await conn.execute(
                    text("""
                        INSERT INTO services (id, tenant_id, name, duration_minutes, price)
                        SELECT UUID(), :tenant_id, 'Pedicure', 60, 40.00
                        WHERE NOT EXISTS (
                            SELECT 1 FROM services WHERE tenant_id = :tenant_id AND name = 'Pedicure'
                        )
                    """),
                    {"tenant_id": tenant_id}
                )
                
                # Criar horários (Segunda a Sexta)
                for day in range(5):
                    await conn.execute(
                        text("""
                            INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
                            SELECT UUID(), :tenant_id, :day, '09:00:00', '18:00:00', false
                            WHERE NOT EXISTS (
                                SELECT 1 FROM schedule_configs WHERE tenant_id = :tenant_id AND day_of_week = :day
                            )
                        """),
                        {"tenant_id": tenant_id, "day": day}
                    )
                
                # Sábado e Domingo fechados
                for day in [5, 6]:
                    await conn.execute(
                        text("""
                            INSERT INTO schedule_configs (id, tenant_id, day_of_week, start_time, end_time, is_closed)
                            SELECT UUID(), :tenant_id, :day, '09:00:00', '18:00:00', true
                            WHERE NOT EXISTS (
                                SELECT 1 FROM schedule_configs WHERE tenant_id = :tenant_id AND day_of_week = :day
                            )
                        """),
                        {"tenant_id": tenant_id, "day": day}
                    )
                
                print("✅ Dados de teste inseridos com sucesso!")
                print("\n📊 Resumo:")
                print("   - Tenant: estudio-bella")
                print("   - Serviços: 3 (Corte de Cabelo, Manicure, Pedicure)")
                print("   - Horários: Segunda a Sexta (09:00 - 18:00)")
        
        await engine.dispose()
        return True
    except Exception as e:
        print(f"❌ Erro ao inserir dados de teste: {e}")
        return False


async def main():
    """Função principal."""
    print("=" * 50)
    print("🚀 Setup do Banco de Dados MySQL")
    print("=" * 50)
    print()
    
    # Verificar configuração
    print(f"📌 URL de conexão: {settings.DATABASE_URL.split('@')[0]}@...")
    print()
    
    # Criar banco
    if not await create_database():
        return
    
    # Criar tabelas
    if not await create_tables():
        return
    
    # Inserir dados de teste
    response = input("\n❓ Deseja inserir dados de teste? (s/n): ").lower().strip()
    if response in ['s', 'sim', 'y', 'yes']:
        await insert_test_data()
    else:
        print("⏭️  Pulando inserção de dados de teste.")
    
    print("\n" + "=" * 50)
    print("✅ Setup concluído com sucesso!")
    print("=" * 50)
    print("\n🚀 Próximo passo:")
    print("   Execute: uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

