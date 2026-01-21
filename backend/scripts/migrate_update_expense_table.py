"""
Script Python para atualizar tabela de Expenses.
Atualiza a estrutura da tabela expenses com os novos campos necessários.
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
    """Verifica se uma coluna existe em uma tabela (PostgreSQL)."""
    try:
        query = text("""
            SELECT COUNT(*) as count
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
        """)
        result = await db.execute(query, {
            "table_name": table_name,
            "column_name": column_name
        })
        row = result.fetchone()
        return row[0] > 0
    except Exception as e:
        print(f"Erro ao verificar coluna {table_name}.{column_name}: {e}")
        return False


async def check_type_exists(db, type_name: str) -> bool:
    """Verifica se um tipo ENUM existe (PostgreSQL)."""
    try:
        query = text("""
            SELECT COUNT(*) as count
            FROM pg_type
            WHERE typname = :type_name
        """)
        result = await db.execute(query, {"type_name": type_name})
        row = result.fetchone()
        return row[0] > 0
    except Exception as e:
        print(f"Erro ao verificar tipo {type_name}: {e}")
        return False


async def migrate():
    """Executa a migração."""
    print("=" * 60)
    print("🔄 Migração: Atualizar tabela de Expenses")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as db:
        try:
            changes_count = 0
            
            # 0. Criar tipo ENUM para payment_method
            print("0. Verificando/criando tipo ENUM payment_method_enum...")
            if not await check_type_exists(db, "payment_method_enum"):
                try:
                    query = text("""
                        CREATE TYPE payment_method_enum AS ENUM(
                            'CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'PIX', 'BANK_TRANSFER'
                        )
                    """)
                    await db.execute(query)
                    await db.commit()
                    print("   ✅ Tipo ENUM payment_method_enum criado")
                    changes_count += 1
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print("   ✅ Tipo ENUM payment_method_enum já existe")
                    else:
                        print(f"   ⚠️ Erro ao criar tipo ENUM: {e}")
                        await db.rollback()
            else:
                print("   ✅ Tipo ENUM payment_method_enum já existe")
            
            # 1. Adicionar item_name
            print("1. Verificando/adicionando coluna item_name...")
            if not await check_column_exists(db, "expenses", "item_name"):
                try:
                    query = text("""
                        ALTER TABLE expenses 
                        ADD COLUMN item_name VARCHAR(200) NULL
                    """)
                    await db.execute(query)
                    
                    comment_query = text("""
                        COMMENT ON COLUMN expenses.item_name IS 'Nome do item comprado (opcional)'
                    """)
                    await db.execute(comment_query)
                    
                    await db.commit()
                    print("   ✅ Coluna item_name adicionada")
                    changes_count += 1
                except Exception as e:
                    print(f"   ⚠️ Erro ao adicionar item_name: {e}")
                    await db.rollback()
            else:
                print("   ✅ Coluna item_name já existe")
            
            # 2. Verificar se payment_method existe
            print("2. Verificando/adicionando coluna payment_method...")
            if not await check_column_exists(db, "expenses", "payment_method"):
                try:
                    query = text("""
                        ALTER TABLE expenses 
                        ADD COLUMN payment_method payment_method_enum 
                        NOT NULL DEFAULT 'CASH'
                    """)
                    await db.execute(query)
                    
                    comment_query = text("""
                        COMMENT ON COLUMN expenses.payment_method IS 'Método de pagamento'
                    """)
                    await db.execute(comment_query)
                    
                    await db.commit()
                    print("   ✅ Coluna payment_method adicionada")
                    changes_count += 1
                except Exception as e:
                    print(f"   ⚠️ Erro ao adicionar payment_method: {e}")
                    await db.rollback()
            else:
                print("   ✅ Coluna payment_method já existe")
            
            # 3. Adicionar payment_date
            print("3. Verificando/adicionando coluna payment_date...")
            if not await check_column_exists(db, "expenses", "payment_date"):
                try:
                    query = text("""
                        ALTER TABLE expenses 
                        ADD COLUMN payment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    """)
                    await db.execute(query)
                    
                    comment_query = text("""
                        COMMENT ON COLUMN expenses.payment_date IS 'Data em que o dinheiro saiu do caixa'
                    """)
                    await db.execute(comment_query)
                    
                    # Copiar date_time para payment_date se houver dados
                    # Verificar se date_time existe antes
                    if await check_column_exists(db, "expenses", "date_time"):
                        update_query = text("""
                            UPDATE expenses 
                            SET payment_date = date_time 
                            WHERE payment_date IS NULL OR payment_date = '1970-01-01 00:00:00'::timestamp
                        """)
                        await db.execute(update_query)
                    
                    await db.commit()
                    print("   ✅ Coluna payment_date adicionada e dados migrados")
                    changes_count += 1
                except Exception as e:
                    print(f"   ⚠️ Erro ao adicionar payment_date: {e}")
                    await db.rollback()
            else:
                print("   ✅ Coluna payment_date já existe")
            
            # 4. Verificar se 'value' precisa ser renomeado para 'amount'
            print("4. Verificando renomeação de 'value' para 'amount'...")
            if await check_column_exists(db, "expenses", "value"):
                if not await check_column_exists(db, "expenses", "amount"):
                    try:
                        query = text("""
                            ALTER TABLE expenses 
                            RENAME COLUMN value TO amount
                        """)
                        await db.execute(query)
                        
                        comment_query = text("""
                            COMMENT ON COLUMN expenses.amount IS 'Valor da despesa'
                        """)
                        await db.execute(comment_query)
                        
                        await db.commit()
                        print("   ✅ Coluna 'value' renomeada para 'amount'")
                        changes_count += 1
                    except Exception as e:
                        print(f"   ⚠️ Erro ao renomear coluna: {e}")
                        await db.rollback()
                else:
                    print("   ✅ Coluna 'amount' já existe (ignorando 'value')")
            else:
                print("   ✅ Coluna 'value' não existe (já foi renomeada)")
            
            # 5. Criar índices se não existirem (PostgreSQL)
            print("5. Verificando índices...")
            try:
                # Verificar índice payment_method
                index_query = text("""
                    SELECT COUNT(*) 
                    FROM pg_indexes 
                    WHERE schemaname = 'public' 
                      AND tablename = 'expenses' 
                      AND indexname = 'idx_expenses_payment_method'
                """)
                result = await db.execute(index_query)
                if result.scalar() == 0:
                    query = text("CREATE INDEX idx_expenses_payment_method ON expenses(payment_method)")
                    await db.execute(query)
                    await db.commit()
                    print("   ✅ Índice idx_expenses_payment_method criado")
                    changes_count += 1
                else:
                    print("   ✅ Índice idx_expenses_payment_method já existe")
                
                # Verificar índice payment_date
                index_query = text("""
                    SELECT COUNT(*) 
                    FROM pg_indexes 
                    WHERE schemaname = 'public' 
                      AND tablename = 'expenses' 
                      AND indexname = 'idx_expenses_payment_date'
                """)
                result = await db.execute(index_query)
                if result.scalar() == 0:
                    query = text("CREATE INDEX idx_expenses_payment_date ON expenses(payment_date)")
                    await db.execute(query)
                    await db.commit()
                    print("   ✅ Índice idx_expenses_payment_date criado")
                    changes_count += 1
                else:
                    print("   ✅ Índice idx_expenses_payment_date já existe")
            except Exception as e:
                print(f"   ⚠️ Erro ao criar índices: {e}")
                await db.rollback()
            
            print()
            print("=" * 60)
            if changes_count > 0:
                print(f"✅ Migração concluída! {changes_count} alteração(ões) realizada(s).")
            else:
                print("✅ Todas as alterações já existem. Nenhuma alteração necessária.")
            print("=" * 60)
            
        except Exception as e:
            print()
            print("=" * 60)
            print(f"❌ Erro durante a migração: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
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
