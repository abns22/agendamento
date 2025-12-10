"""
Script Python para adicionar tabelas de Transaction e PaymentEntry.
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
    print("🔄 Migração: Adicionar tabelas de Transaction e PaymentEntry")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # 1. Adicionar campos de histórico ao Appointment
            print("1. Adicionando campos de histórico ao Appointment...")
            fields = [
                ("final_sale_value", "DECIMAL(10, 2) NULL COMMENT 'Valor final de venda (para histórico)'"),
                ("service_cost", "DECIMAL(10, 2) NULL COMMENT 'Custo do serviço (para histórico)'")
            ]
            
            for column_name, column_def in fields:
                added = await add_column_if_not_exists(db, "appointments", column_def, column_name)
                if added:
                    added_count += 1
            
            # 2. Criar tabela transactions
            print("\n2. Criando tabela transactions...")
            create_transactions_table = """
                CREATE TABLE transactions (
                    id CHAR(36) PRIMARY KEY,
                    tenant_id CHAR(36) NOT NULL,
                    appointment_id CHAR(36) NOT NULL,
                    date_time DATETIME NOT NULL COMMENT 'Data/hora da transação (UTC)',
                    gross_value DECIMAL(10, 2) NOT NULL COMMENT 'Valor bruto (antes das taxas)',
                    net_value DECIMAL(10, 2) NOT NULL COMMENT 'Valor líquido (após taxas)',
                    total_cost DECIMAL(10, 2) NOT NULL COMMENT 'Soma dos custos fixos dos serviços',
                    total_profit DECIMAL(10, 2) NOT NULL COMMENT 'Lucro (net_value - total_cost)',
                    additional_cost DECIMAL(10, 2) NULL COMMENT 'Custo adicional opcional',
                    INDEX idx_transactions_tenant_id (tenant_id),
                    INDEX idx_transactions_appointment_id (appointment_id),
                    INDEX idx_transactions_date_time (date_time),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_transactions_table, "transactions")
            if added:
                added_count += 1
            
            # 3. Criar tabela payment_entries
            print("\n3. Criando tabela payment_entries...")
            create_payment_entries_table = """
                CREATE TABLE payment_entries (
                    id CHAR(36) PRIMARY KEY,
                    transaction_id CHAR(36) NOT NULL,
                    payment_method_id CHAR(36) NOT NULL,
                    value_paid DECIMAL(10, 2) NOT NULL COMMENT 'Valor parcial pago nesta forma',
                    installments INT NULL COMMENT 'Número de parcelas (apenas para crédito)',
                    is_bank_account BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'True se for PIX/Cartão',
                    INDEX idx_payment_entries_transaction_id (transaction_id),
                    INDEX idx_payment_entries_payment_method_id (payment_method_id),
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (payment_method_id) REFERENCES payment_method_configs(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_payment_entries_table, "payment_entries")
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

