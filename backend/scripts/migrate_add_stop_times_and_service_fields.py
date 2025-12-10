"""
Script Python para adicionar campos ao Service e criar tabela stop_times.
Executa a migração SQL de forma segura, verificando se as colunas/tabelas
já existem antes de tentar criá-las.
"""
import asyncio
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Garantir que o .env seja carregado do diretório backend
os.chdir(backend_dir)

from app.core.database import AsyncSessionLocal
from sqlalchemy import text
from sqlalchemy.exc import OperationalError


async def check_column_exists(db, table_name: str, column_name: str) -> bool:
    """Verifica se uma coluna existe na tabela."""
    try:
        query = text("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
        """)
        result = await db.execute(query, {"table_name": table_name, "column_name": column_name})
        row = result.fetchone()
        return row[0] > 0
    except Exception as e:
        print(f"Erro ao verificar coluna {table_name}.{column_name}: {e}")
        return False


async def check_table_exists(db, table_name: str) -> bool:
    """Verifica se uma tabela existe."""
    try:
        query = text("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
        """)
        result = await db.execute(query, {"table_name": table_name})
        row = result.fetchone()
        return row[0] > 0
    except Exception as e:
        print(f"Erro ao verificar tabela {table_name}: {e}")
        return False


async def add_column_if_not_exists(db, table_name: str, column_def: str, column_name: str):
    """Adiciona uma coluna apenas se ela não existir."""
    exists = await check_column_exists(db, table_name, column_name)
    if exists:
        print(f"✅ Coluna '{column_name}' já existe, pulando...")
        return False
    
    try:
        query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
        await db.execute(query)
        await db.commit()
        print(f"✅ Coluna '{column_name}' adicionada com sucesso!")
        return True
    except OperationalError as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print(f"⚠️ Coluna '{column_name}' já existe (erro ignorado)")
            return False
        raise
    except Exception as e:
        await db.rollback()
        print(f"❌ Erro ao adicionar coluna '{column_name}': {e}")
        raise


async def create_table_if_not_exists(db, create_table_sql: str, table_name: str):
    """Cria uma tabela apenas se ela não existir."""
    exists = await check_table_exists(db, table_name)
    if exists:
        print(f"✅ Tabela '{table_name}' já existe, pulando...")
        return False
    
    try:
        query = text(create_table_sql)
        await db.execute(query)
        await db.commit()
        print(f"✅ Tabela '{table_name}' criada com sucesso!")
        return True
    except OperationalError as e:
        if "already exists" in str(e).lower() or "1050" in str(e):
            print(f"⚠️ Tabela '{table_name}' já existe (erro ignorado)")
            return False
        raise
    except Exception as e:
        await db.rollback()
        print(f"❌ Erro ao criar tabela '{table_name}': {e}")
        raise


async def migrate():
    """Executa a migração."""
    print("=" * 60)
    print("🔄 Migração: Adicionar campos ao Service e criar tabela stop_times")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # 1. Adicionar campo display_color_code ao Service
            print("1. Adicionando campo display_color_code ao Service...")
            added = await add_column_if_not_exists(
                db, 
                "services", 
                "display_color_code VARCHAR(7) NULL COMMENT 'Cor de exibição na Agenda Admin (ex: #4A90E2)' AFTER promotion_color_code",
                "display_color_code"
            )
            if added:
                added_count += 1
            
            # 2. Adicionar campo long_description ao Service
            print("\n2. Adicionando campo long_description ao Service...")
            added = await add_column_if_not_exists(
                db, 
                "services", 
                "long_description TEXT NULL COMMENT 'Descrição detalhada do serviço' AFTER display_color_code",
                "long_description"
            )
            if added:
                added_count += 1
            
            # 3. Criar tabela stop_times
            print("\n3. Criando tabela stop_times...")
            create_stop_times_table = """
                CREATE TABLE stop_times (
                    id CHAR(36) PRIMARY KEY,
                    tenant_id CHAR(36) NOT NULL,
                    day_of_week INT NOT NULL COMMENT 'Dia da semana (0=Segunda, 6=Domingo)',
                    start_time TIME NOT NULL COMMENT 'Horário de início da parada (ex: 12:00)',
                    end_time TIME NOT NULL COMMENT 'Horário de fim da parada (ex: 13:00)',
                    description VARCHAR(200) NULL COMMENT 'Descrição opcional (ex: Almoço, Pausa)',
                    INDEX idx_stop_times_tenant_id (tenant_id),
                    INDEX idx_stop_times_day_of_week (day_of_week),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_stop_times_table, "stop_times")
            if added:
                added_count += 1
            
            print()
            print("=" * 60)
            if added_count > 0:
                print(f"✅ Migração concluída! {added_count} alteração(ões) realizada(s).")
            else:
                print("✅ Todas as alterações já existem. Nenhuma alteração necessária.")
            print("=" * 60)
            
        except Exception as e:
            print()
            print("=" * 60)
            print(f"❌ Erro durante a migração: {e}")
            print("=" * 60)
            raise


if __name__ == "__main__":
    try:
        asyncio.run(migrate())
    except KeyboardInterrupt:
        print("\n\n⚠️ Migração cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Erro inesperado: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)

