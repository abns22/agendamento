"""
Script Python para adicionar campos financeiros.
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
        query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
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
    print("🔄 Migração: Adicionar campos financeiros")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # 1. Adicionar fixed_cost_value ao Service
            print("1. Adicionando fixed_cost_value ao Service...")
            added = await add_column_if_not_exists(
                db,
                "services",
                "DECIMAL(10, 2) NULL COMMENT 'Custo fixo do serviço (para cálculo de lucro)'",
                "fixed_cost_value"
            )
            if added:
                added_count += 1
            
            # 2. Criar tabela payment_method_configs
            print("\n2. Criando tabela payment_method_configs...")
            create_payment_method_table = """
                CREATE TABLE payment_method_configs (
                    id CHAR(36) PRIMARY KEY,
                    tenant_id CHAR(36) NOT NULL,
                    method_name VARCHAR(100) NOT NULL COMMENT 'Nome da forma de pagamento',
                    is_editable BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Se pode ser editada',
                    max_installments INT NULL COMMENT 'Máximo de parcelas',
                    debit_tax_type VARCHAR(10) NULL COMMENT 'Tipo de taxa de débito: % ou R$',
                    debit_tax_value DECIMAL(10, 2) NULL COMMENT 'Valor da taxa de débito',
                    INDEX idx_payment_method_configs_tenant_id (tenant_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_payment_method_table, "payment_method_configs")
            if added:
                added_count += 1
            
            # 3. Criar tabela payment_installment_configs
            print("\n3. Criando tabela payment_installment_configs...")
            create_installment_table = """
                CREATE TABLE payment_installment_configs (
                    id CHAR(36) PRIMARY KEY,
                    payment_method_id CHAR(36) NOT NULL,
                    installments_count INT NOT NULL COMMENT 'Número de parcelas',
                    tax_type ENUM('%', 'R$') NOT NULL COMMENT 'Tipo de taxa',
                    tax_value DECIMAL(10, 2) NOT NULL COMMENT 'Valor da taxa',
                    INDEX idx_payment_installment_configs_payment_method_id (payment_method_id),
                    UNIQUE KEY uq_payment_method_installments (payment_method_id, installments_count),
                    FOREIGN KEY (payment_method_id) REFERENCES payment_method_configs(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_installment_table, "payment_installment_configs")
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

