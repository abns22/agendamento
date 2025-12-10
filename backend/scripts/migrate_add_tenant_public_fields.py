"""
Script Python para adicionar campos públicos ao modelo Tenant.

Este script executa a migração SQL de forma segura, verificando se as colunas
já existem antes de tentar adicioná-las.
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


async def add_column_if_not_exists(db, table_name: str, column_def: str, column_name: str):
    """Adiciona uma coluna apenas se ela não existir."""
    exists = await check_column_exists(db, table_name, column_name)
    if exists:
        print(f"✅ Coluna '{column_name}' já existe, pulando...")
        return False
    
    try:
        # Incluir o nome da coluna na definição: "nome_coluna TIPO ..."
        query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        await db.execute(query)
        await db.commit()
        print(f"✅ Coluna '{column_name}' adicionada com sucesso!")
        return True
    except OperationalError as e:
        # Se a coluna já existe (erro 1060), apenas avisar
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print(f"⚠️ Coluna '{column_name}' já existe (erro ignorado)")
            return False
        raise
    except Exception as e:
        await db.rollback()
        print(f"❌ Erro ao adicionar coluna '{column_name}': {e}")
        raise


async def migrate():
    """Executa a migração."""
    print("=" * 60)
    print("🔄 Migração: Adicionar campos públicos ao Tenant")
    print("=" * 60)
    print()
    
    columns_to_add = [
        ("name", "VARCHAR(200) NULL COMMENT 'Nome do estúdio (ex: Estúdio Bella)'"),
        ("logo_url", "VARCHAR(500) NULL COMMENT 'URL da logo do estúdio'"),
        ("description", "TEXT NULL COMMENT 'Breve descrição do estúdio'"),
        ("address", "TEXT NULL COMMENT 'Endereço físico do estúdio'"),
        ("phone_contact", "VARCHAR(20) NULL COMMENT 'Número de telefone público para contato'"),
        ("schedule_display_text", "VARCHAR(200) NULL COMMENT 'Texto amigável do horário de funcionamento'"),
    ]
    
    # Nota: column_def já contém apenas o tipo e constraints, o nome vem separado
    
    async with AsyncSessionLocal() as db:
        try:
            added_count = 0
            for column_name, column_def in columns_to_add:
                added = await add_column_if_not_exists(db, "tenants", column_def, column_name)
                if added:
                    added_count += 1
            
            print()
            print("=" * 60)
            if added_count > 0:
                print(f"✅ Migração concluída! {added_count} coluna(s) adicionada(s).")
            else:
                print("✅ Todas as colunas já existem. Nenhuma alteração necessária.")
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
        sys.exit(1)

