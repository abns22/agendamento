"""
Script Python para criar tabelas de inventário.
Executa a migração SQL de forma segura, verificando se as tabelas já existem.
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
    print("🔄 Migração: Criar tabelas de inventário")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # Criar tabela product_categories
            print("1. Criando tabela product_categories...")
            create_categories_table = """
                CREATE TABLE product_categories (
                    id CHAR(36) PRIMARY KEY,
                    tenant_id CHAR(36) NOT NULL,
                    name VARCHAR(200) NOT NULL COMMENT 'Nome da categoria',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_product_categories_tenant_id (tenant_id),
                    INDEX idx_product_categories_name (name),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_categories_table, "product_categories")
            if added:
                added_count += 1
            
            # Criar tabela products
            print("2. Criando tabela products...")
            create_products_table = """
                CREATE TABLE products (
                    id CHAR(36) PRIMARY KEY,
                    tenant_id CHAR(36) NOT NULL,
                    category_id CHAR(36) NULL COMMENT 'ID da categoria (opcional)',
                    name VARCHAR(200) NOT NULL COMMENT 'Nome do produto',
                    unit_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'Custo unitário de aquisição',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_products_tenant_id (tenant_id),
                    INDEX idx_products_category_id (category_id),
                    INDEX idx_products_name (name),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES product_categories(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_products_table, "products")
            if added:
                added_count += 1
            
            # Criar tabela stock_entries
            print("3. Criando tabela stock_entries...")
            create_stock_entries_table = """
                CREATE TABLE stock_entries (
                    id CHAR(36) PRIMARY KEY,
                    product_id CHAR(36) NOT NULL,
                    unit_type ENUM('UNITARIO', 'PACOTE', 'CAIXA') NOT NULL DEFAULT 'UNITARIO' COMMENT 'Tipo de unidade',
                    quantity INT NOT NULL DEFAULT 0 COMMENT 'Quantidade em estoque',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_stock_entries_product_id (product_id),
                    INDEX idx_stock_entries_unit_type (unit_type),
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            added = await create_table_if_not_exists(db, create_stock_entries_table, "stock_entries")
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

