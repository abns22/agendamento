"""
Script para deletar transações de um tenant específico.

Uso:
    python delete_transactions.py --email myrela.martins2006@icloud.com --transaction-ids id1 id2 id3
    
    OU
    
    python delete_transactions.py --email myrela.martins2006@icloud.com --list-only
    
    Para listar transações e depois deletar:
    python delete_transactions.py --email myrela.martins2006@icloud.com --transaction-ids id1 id2 id3 --confirm
"""
import asyncio
import sys
import argparse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, and_
from app.models.transaction import Transaction
from app.models.user import User
from app.models.payment_entry import PaymentEntry
from app.core.config import settings
from app.core.database import get_database_url
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def get_tenant_id_by_email(db: AsyncSession, email: str):
    """Busca o tenant_id a partir do email do usuário."""
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"Usuário com email {email} não encontrado")
    return str(user.tenant_id)


async def list_transactions(db: AsyncSession, tenant_id: str, limit: int = 20):
    """Lista as últimas transações do tenant."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.tenant_id == tenant_id)
        .order_by(Transaction.date_time.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()
    return transactions


async def delete_transactions(db: AsyncSession, tenant_id: str, transaction_ids: list):
    """Deleta transações específicas de um tenant."""
    # Verificar se as transações pertencem ao tenant
    for transaction_id in transaction_ids:
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.id == transaction_id,
                    Transaction.tenant_id == tenant_id
                )
            )
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            raise ValueError(f"Transação {transaction_id} não encontrada ou não pertence ao tenant")
    
    # Deletar payment_entries primeiro (por segurança, mesmo com cascade)
    for transaction_id in transaction_ids:
        result = await db.execute(
            select(PaymentEntry).where(PaymentEntry.transaction_id == transaction_id)
        )
        payment_entries = result.scalars().all()
        for pe in payment_entries:
            await db.delete(pe)
    
    # Deletar as transações
    for transaction_id in transaction_ids:
        result = await db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        if transaction:
            await db.delete(transaction)
    
    await db.commit()
    return len(transaction_ids)


async def main():
    parser = argparse.ArgumentParser(description='Deletar transações de um tenant')
    parser.add_argument('--email', required=True, help='Email do tenant')
    parser.add_argument('--transaction-ids', nargs='+', help='IDs das transações para deletar')
    parser.add_argument('--list-only', action='store_true', help='Apenas listar transações')
    parser.add_argument('--confirm', action='store_true', help='Confirmar deleção')
    
    args = parser.parse_args()
    
    # Criar engine e session
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Buscar tenant_id
            tenant_id = await get_tenant_id_by_email(db, args.email)
            print(f"✅ Tenant ID encontrado: {tenant_id}")
            
            # Listar transações
            transactions = await list_transactions(db, tenant_id, limit=20)
            print(f"\n📋 Transações encontradas: {len(transactions)}")
            print("\n" + "="*80)
            for i, t in enumerate(transactions, 1):
                print(f"{i}. ID: {t.id}")
                print(f"   Data: {t.date_time}")
                print(f"   Valor Bruto: R$ {t.gross_value}")
                print(f"   Valor Líquido: R$ {t.net_value}")
                print(f"   Desconto: R$ {t.discount}")
                print("-" * 80)
            
            if args.list_only:
                return
            
            # Deletar transações
            if args.transaction_ids:
                if not args.confirm:
                    print(f"\n⚠️  ATENÇÃO: Você está prestes a deletar {len(args.transaction_ids)} transações!")
                    print("IDs das transações a serem deletadas:")
                    for tid in args.transaction_ids:
                        print(f"  - {tid}")
                    print("\nPara confirmar, execute novamente com --confirm")
                    return
                
                deleted_count = await delete_transactions(db, tenant_id, args.transaction_ids)
                print(f"\n✅ {deleted_count} transações deletadas com sucesso!")
            else:
                print("\n❌ Nenhuma transação especificada para deletar")
                print("Use --transaction-ids id1 id2 id3 para especificar os IDs")
        
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Erro: {str(e)}")
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())

