"""
Script Python para adicionar campo cancellation_reason à tabela appointments.
Execute: python backend/scripts/migrate_add_cancellation_reason.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
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


async def add_column_if_not_exists(db, table_name: str, column_name: str, column_def: str):
    """Adiciona uma coluna apenas se ela não existir."""
    exists = await check_column_exists(db, table_name, column_name)
    if exists:
        print(f"✅ Coluna '{column_name}' já existe na tabela '{table_name}', pulando...")
        return False
    
    try:
        query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
        await db.execute(query)
        await db.commit()
        print(f"✅ Coluna '{column_name}' adicionada com sucesso à tabela '{table_name}'!")
        return True
    except OperationalError as e:
        error_msg = str(e).lower()
        if "duplicate column" in error_msg or "already exists" in error_msg or "1060" in str(e):
            print(f"⚠️ Coluna '{column_name}' já existe na tabela '{table_name}' (erro ignorado)")
            return False
        raise
    except Exception as e:
        await db.rollback()
        print(f"❌ Erro ao adicionar coluna '{column_name}': {e}")
        raise


async def migrate():
    """Executa a migração."""
    print("=" * 60)
    print("🔄 Migração: Adicionar campo cancellation_reason à tabela appointments")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            
            # Adicionar coluna cancellation_reason
            print("1. Adicionando coluna cancellation_reason...")
            column_def = "cancellation_reason TEXT NULL COMMENT 'Motivo do cancelamento (quando status = CANCELED)'"
            added = await add_column_if_not_exists(db, "appointments", "cancellation_reason", column_def)
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

