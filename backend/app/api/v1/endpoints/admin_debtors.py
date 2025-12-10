"""
Endpoints administrativos para gerenciamento de Devedores (Contas a Receber).
"""
from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.debtor import Debtor, DebtorStatus
from app.models.transaction import Transaction
from app.models.payment_entry import PaymentEntry
from app.models.payment_method_config import PaymentMethodConfig

from app.schemas.debtor import (
    DebtorResponse,
    SettleDebtorRequest,
    SettleDebtorResponse
)

router = APIRouter(prefix="/admin/debtors", tags=["Admin - Debtors"])


@router.get(
    "",
    response_model=list[DebtorResponse],
    summary="Listar devedores",
    description="Retorna todos os devedores (contas a receber) do tenant autenticado."
)
async def list_debtors(
    status: str = None,  # 'PENDING' ou 'PAID'
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os devedores do tenant.
    
    Args:
        status: Filtrar por status ('PENDING' ou 'PAID')
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[DebtorResponse]: Lista de devedores ordenados por data de vencimento
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="tenant_id inválido")
    
    # Buscar transações do tenant para filtrar devedores
    transactions_query = select(Transaction.id).where(
        Transaction.tenant_id == tenant_id_str
    )
    transactions_result = await db.execute(transactions_query)
    transaction_ids = [str(row[0]) for row in transactions_result.fetchall()]
    
    if not transaction_ids:
        return []
    
    # Buscar devedores vinculados às transações do tenant
    query = select(Debtor).where(Debtor.transaction_id.in_(transaction_ids))
    
    # Filtrar por status se fornecido
    if status:
        try:
            debtor_status = DebtorStatus(status.upper())
            query = query.where(Debtor.status == debtor_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="status deve ser 'PENDING' ou 'PAID'")
    
    # Ordenar por data de vencimento (mais próximos primeiro)
    query = query.order_by(Debtor.due_date.asc())
    
    result = await db.execute(query)
    debtors = result.scalars().all()
    
    return [DebtorResponse.model_validate(debtor) for debtor in debtors]


@router.get(
    "/{debtor_id}",
    response_model=DebtorResponse,
    summary="Obter devedor",
    description="Retorna um devedor específico."
)
async def get_debtor(
    debtor_id: UUID = Path(..., description="UUID do devedor"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtém um devedor específico.
    
    Args:
        debtor_id: UUID do devedor
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        DebtorResponse: Dados do devedor
        
    Raises:
        HTTPException 404: Se o devedor não for encontrado
    """
    tenant_id_str = str(tenant.id) if tenant.id else None
    debtor_id_str = str(debtor_id) if debtor_id else None
    
    if not tenant_id_str or not debtor_id_str:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    
    # Buscar devedor
    result = await db.execute(
        select(Debtor).where(Debtor.id == debtor_id_str)
    )
    debtor = result.scalar_one_or_none()
    
    if not debtor:
        raise HTTPException(status_code=404, detail="Devedor não encontrado")
    
    # Validar que a transação pertence ao tenant
    transaction_query = select(Transaction).where(
        and_(
            Transaction.id == str(debtor.transaction_id),
            Transaction.tenant_id == tenant_id_str
        )
    )
    transaction_result = await db.execute(transaction_query)
    transaction = transaction_result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Devedor não encontrado ou não pertence ao tenant")
    
    return DebtorResponse.model_validate(debtor)


@router.post(
    "/{debtor_id}/settle",
    response_model=SettleDebtorResponse,
    status_code=200,
    summary="Dar baixa em devedor",
    description="Registra o pagamento de uma conta a receber e cria PaymentEntry na Transaction original."
)
async def settle_debtor(
    debtor_id: UUID = Path(..., description="UUID do devedor"),
    settle_data: SettleDebtorRequest = ...,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Dá baixa em uma conta a receber.
    
    Esta rota:
    1. Valida o devedor
    2. Atualiza status para PAID
    3. Cria PaymentEntry na Transaction original com a forma de pagamento real
    4. Atualiza Transaction.is_paid para True
    
    Args:
        debtor_id: UUID do devedor
        settle_data: Dados de baixa (forma de pagamento)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        SettleDebtorResponse: Devedor atualizado e PaymentEntry criado
        
    Raises:
        HTTPException 404: Se o devedor não for encontrado
        HTTPException 400: Se o devedor já foi pago ou dados inválidos
        HTTPException 500: Erro interno do servidor
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        debtor_id_str = str(debtor_id) if debtor_id else None
        
        if not tenant_id_str or not debtor_id_str:
            raise HTTPException(status_code=400, detail="IDs inválidos")
        
        # 1. Buscar devedor
        debtor_query = select(Debtor).where(Debtor.id == debtor_id_str)
        debtor_result = await db.execute(debtor_query)
        debtor = debtor_result.scalar_one_or_none()
        
        if not debtor:
            raise HTTPException(status_code=404, detail="Devedor não encontrado")
        
        # 2. Validar que a transação pertence ao tenant
        transaction_query = select(Transaction).where(
            and_(
                Transaction.id == str(debtor.transaction_id),
                Transaction.tenant_id == tenant_id_str
            )
        )
        transaction_result = await db.execute(transaction_query)
        transaction = transaction_result.scalar_one_or_none()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transação não encontrada ou não pertence ao tenant")
        
        # 3. Validar que ainda está pendente
        if debtor.status == DebtorStatus.PAID:
            raise HTTPException(status_code=400, detail="Esta conta já foi quitada")
        
        # 4. Buscar forma de pagamento
        payment_method_id_str = str(settle_data.payment_method_id)
        payment_method_query = select(PaymentMethodConfig).where(
            and_(
                PaymentMethodConfig.id == payment_method_id_str,
                PaymentMethodConfig.tenant_id == tenant_id_str
            )
        )
        payment_method_result = await db.execute(payment_method_query)
        payment_method = payment_method_result.scalar_one_or_none()
        
        if not payment_method:
            raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
        
        # 5. Calcular taxa de pagamento (se houver)
        from app.services.financial_service import FinancialService
        
        value_to_pay = Decimal(str(debtor.value_due))
        installments = settle_data.installments if settle_data.installments and settle_data.installments > 1 else 1
        
        fee, _ = await FinancialService.calculate_payment_fee(
            db_session=db,
            tenant_id=tenant.id,
            payment_method_id=settle_data.payment_method_id,
            service_price=value_to_pay,
            installments=installments
        )
        
        # O valor pago é o valor devido (já está no net_value da transaction)
        # A taxa será descontada do valor que entra no caixa
        value_paid = value_to_pay
        net_value_received = value_paid - fee
        
        # 6. Determinar se é conta bancária (PIX ou Cartão)
        # Dinheiro = False (físico), PIX/Cartões = True (bancário)
        method_name_lower = payment_method.method_name.lower()
        is_bank_account = (
            'pix' in method_name_lower or
            'cartão' in method_name_lower or
            'card' in method_name_lower or
            'débito' in method_name_lower or
            'debit' in method_name_lower or
            'crédito' in method_name_lower or
            'credit' in method_name_lower
        ) and 'dinheiro' not in method_name_lower and 'cash' not in method_name_lower
        
        # 7. Criar PaymentEntry na Transaction original
        payment_entry = PaymentEntry(
            transaction_id=str(transaction.id),
            payment_method_id=payment_method_id_str,
            value_paid=value_paid,
            installments=settle_data.installments if settle_data.installments and settle_data.installments > 1 else None,
            is_bank_account=is_bank_account
        )
        
        db.add(payment_entry)
        
        # 8. Atualizar Transaction.is_paid para True
        transaction.is_paid = True
        
        # 9. Atualizar Debtor
        debtor.status = DebtorStatus.PAID
        debtor.paid_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(debtor)
        await db.refresh(payment_entry)
        
        # Construir resposta
        payment_entry_dict = {
            'id': str(payment_entry.id),
            'transaction_id': str(payment_entry.transaction_id),
            'payment_method_id': UUID(str(payment_entry.payment_method_id)),
            'value_paid': payment_entry.value_paid,
            'installments': payment_entry.installments,
            'is_bank_account': payment_entry.is_bank_account
        }
        
        return SettleDebtorResponse(
            debtor=DebtorResponse.model_validate(debtor),
            payment_entry=payment_entry_dict,
            message="Dívida quitada com sucesso"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao dar baixa no devedor: {str(e)}"
        )

