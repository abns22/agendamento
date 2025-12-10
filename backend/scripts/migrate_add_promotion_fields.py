"""
Script Python para adicionar campos de promoção ao Service.
Executa a migração SQL de forma segura, verificando se as colunas
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


async def check_index_exists(db, index_name: str) -> bool:
    """Verifica se um índice existe."""
    try:
        query = text("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND INDEX_NAME = :index_name
        """)
        result = await db.execute(query, {"index_name": index_name})
        row = result.fetchone()
        return row[0] > 0
    except Exception as e:
        print(f"Erro ao verificar índice {index_name}: {e}")
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


async def create_index_if_not_exists(db, index_sql: str, index_name: str):
    """Cria um índice apenas se ele não existir."""
    exists = await check_index_exists(db, index_name)
    if exists:
        print(f"✅ Índice '{index_name}' já existe, pulando...")
        return False
    
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


async def migrate():
    """Executa a migração."""
    print("=" * 60)
    print("🔄 Migração: Adicionar campos de promoção ao Service")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # Adicionar campos de promoção
            print("1. Adicionando campos de promoção...")
            
            fields = [
                ("is_promotional", "BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Se o serviço está em promoção'"),
                ("promotion_start_date", "DATETIME NULL COMMENT 'Data/hora de início da promoção (UTC)'"),
                ("promotion_end_date", "DATETIME NULL COMMENT 'Data/hora de fim da promoção (UTC)'"),
                ("promotional_value", "DECIMAL(10, 2) NULL COMMENT 'Valor promocional do serviço'"),
                ("promotion_display_name", "VARCHAR(200) NULL COMMENT 'Nome da promoção'"),
                ("promotion_description", "TEXT NULL COMMENT 'Descrição/observação da promoção'"),
                ("promotion_color_code", "VARCHAR(7) NULL COMMENT 'Código hex da cor da promoção'")
            ]
            
            for column_name, column_def in fields:
                added = await add_column_if_not_exists(db, "services", column_def, column_name)
                if added:
                    added_count += 1
            
            # Criar índice
            print("\n2. Criando índice para is_promotional...")
            added = await create_index_if_not_exists(
                db,
                "CREATE INDEX idx_services_is_promotional ON services(is_promotional)",
                "idx_services_is_promotional"
            )
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

