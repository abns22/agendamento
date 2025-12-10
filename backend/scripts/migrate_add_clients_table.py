"""
Script Python para criar tabela clients.
Executa a migração SQL de forma segura, verificando se a tabela já existe.
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
    print("🔄 Migração: Criar tabela clients")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # Criar tabela clients
            print("1. Criando tabela clients...")
            create_clients_table = """
                CREATE TABLE clients (
                    id CHAR(36) PRIMARY KEY,
                    tenant_id CHAR(36) NOT NULL,
                    name VARCHAR(200) NOT NULL COMMENT 'Nome completo do cliente',
                    phone_number VARCHAR(20) NOT NULL COMMENT 'Número de telefone do cliente',
                    email VARCHAR(200) NULL COMMENT 'Email do cliente (opcional)',
                    birth_date DATE NULL COMMENT 'Data de nascimento (para aniversários)',
                    INDEX idx_clients_tenant_id (tenant_id),
                    INDEX idx_clients_name (name),
                    INDEX idx_clients_phone_number (phone_number),
                    INDEX idx_clients_birth_date (birth_date),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_clients_table, "clients")
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

