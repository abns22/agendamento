"""
Script Python para criar tabela de Debtors e adicionar campo is_paid ao Transaction.
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
        print(f"Erro ao verificar coluna {column_name}: {e}")
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
        # column_def já deve conter o nome da coluna e sua definição completa
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


async def create_index_if_not_exists(db, index_sql: str, index_name: str):
    """Cria um índice apenas se ele não existir."""
    try:
        query = text(index_sql)
        await db.execute(query)
        await db.commit()
        print(f"✅ Índice '{index_name}' criado com sucesso!")
        return True
    except OperationalError as e:
        if "Duplicate key name" in str(e) or "1061" in str(e):
            print(f"⚠️ Índice '{index_name}' já existe (erro ignorado)")
            return False
        raise
    except Exception as e:
        await db.rollback()
        print(f"❌ Erro ao criar índice '{index_name}': {e}")
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
        if "already exists" in str(e) or "1050" in str(e):
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
    print("🔄 Migração: Criar tabela de Debtors e adicionar is_paid ao Transaction")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # 1. Adicionar campo is_paid ao Transaction
            print("1. Adicionando campo is_paid ao Transaction...")
            added = await add_column_if_not_exists(
                db, 
                "transactions", 
                "is_paid BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'True se foi pago, False se é a prazo'",
                "is_paid"
            )
            if added:
                added_count += 1
            
            # Criar índice para is_paid
            print("\n2. Criando índice para is_paid...")
            added = await create_index_if_not_exists(
                db,
                "CREATE INDEX idx_transactions_is_paid ON transactions(is_paid)",
                "idx_transactions_is_paid"
            )
            if added:
                added_count += 1
            
            # 3. Criar tabela debtors
            print("\n3. Criando tabela debtors...")
            create_debtors_table = """
                CREATE TABLE debtors (
                    id CHAR(36) PRIMARY KEY,
                    transaction_id CHAR(36) NOT NULL,
                    client_name VARCHAR(200) NOT NULL COMMENT 'Nome do cliente devedor',
                    client_phone VARCHAR(20) NULL COMMENT 'Telefone do cliente',
                    due_date DATETIME NOT NULL COMMENT 'Data de vencimento (UTC)',
                    value_due DECIMAL(10, 2) NOT NULL COMMENT 'Valor devido',
                    status ENUM('PENDING', 'PAID') NOT NULL DEFAULT 'PENDING' COMMENT 'Status do devedor',
                    paid_at DATETIME NULL COMMENT 'Data/hora do pagamento',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_debtors_transaction_id (transaction_id),
                    INDEX idx_debtors_due_date (due_date),
                    INDEX idx_debtors_status (status),
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_debtors_table, "debtors")
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
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️ Migração cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

