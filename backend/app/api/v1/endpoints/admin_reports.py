"""
Endpoints administrativos para Relatórios e Caixa.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from uuid import UUID
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import verify_subscription_access
from app.models.tenant import Tenant
from app.models.transaction import Transaction
from app.models.payment_entry import PaymentEntry
from app.models.payment_method_config import PaymentMethodConfig
from app.models.appointment import Appointment
from app.models.service import Service
from app.models.expense import Expense, PaymentMethodEnum as ExpensePaymentMethodEnum
from app.models.client import Client

from app.schemas.report import (
    CashSummaryResponse,
    PaymentMethodSummary,
    TransactionDetailResponse,
    PaymentEntryDetail,
    TransactionsListResponse,
    DetailedCashSummaryResponse,
    GeneralSummary,
    BreakdownCategory,
    BreakdownSummary,
    MethodsDetailed
)
from app.schemas.client import BirthdayClientResponse

router = APIRouter(prefix="/admin/reports", tags=["Admin - Reports"])


def is_cash_payment_method(payment_method_name: str) -> bool:
    """
    Determina se um método de pagamento é CASH (dinheiro físico).
    
    Args:
        payment_method_name: Nome do método de pagamento
        
    Returns:
        True se for dinheiro físico, False caso contrário
    """
    method_lower = payment_method_name.lower().strip()
    return 'dinheiro' in method_lower or 'cash' in method_lower


def get_expense_payment_category(expense_payment_method) -> str:
    """
    Determina a categoria de uma despesa (CASH ou BANCO).
    
    Args:
        expense_payment_method: PaymentMethodEnum da despesa
        
    Returns:
        'CASH' ou 'BANCO'
    """
    if expense_payment_method == ExpensePaymentMethodEnum.CASH:
        return 'CASH'
    return 'BANCO'


def get_payment_method_detailed_key(payment_method_name: str) -> Optional[str]:
    """
    Retorna a chave detalhada do método de pagamento.
    
    Args:
        payment_method_name: Nome do método de pagamento
        
    Returns:
        Chave para methods_detailed ou None
    """
    method_lower = payment_method_name.lower().strip()
    if 'pix' in method_lower:
        return 'pix'
    elif 'crédito' in method_lower or 'credit' in method_lower:
        return 'credit_card'
    elif 'débito' in method_lower or 'debit' in method_lower:
        return 'debit_card'
    elif 'dinheiro' in method_lower or 'cash' in method_lower:
        return 'cash'
    elif 'transferência' in method_lower or 'transfer' in method_lower:
        return 'bank_transfer'
    return None


@router.get(
    "/cash-summary-detailed",
    response_model=DetailedCashSummaryResponse,
    summary="Resumo Detalhado do Caixa",
    description="Retorna resumo financeiro detalhado separando Caixa Físico e Banco/Digital."
)
async def get_detailed_cash_summary(
    start_date: Optional[str] = Query(None, description="Data de início no formato YYYY-MM-DD. Se não fornecido, usa hoje."),
    end_date: Optional[str] = Query(None, description="Data de fim no formato YYYY-MM-DD. Se não fornecido, usa hoje."),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna resumo financeiro detalhado separando Caixa Físico e Banco/Digital.
    
    Calcula:
    - Entradas separadas por categoria (CASH vs BANCO)
    - Despesas separadas por categoria
    - Saldos líquidos por categoria
    - Detalhamento por método de pagamento
    
    IMPORTANTE: Contas a receber PENDING não são incluídas nos cálculos.
    
    Args:
        start_date: Data de início no formato YYYY-MM-DD (opcional, padrão: hoje)
        end_date: Data de fim no formato YYYY-MM-DD (opcional, padrão: hoje)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        DetailedCashSummaryResponse: Resumo detalhado do caixa
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(status_code=400, detail="tenant_id inválido")
        
        # Determinar período
        today = datetime.now().date()
        
        if not start_date and not end_date:
            start_date_str = today.strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif start_date and not end_date:
            end_date_str = start_date
            start_date_str = start_date
        elif not start_date and end_date:
            start_date_str = end_date
            end_date_str = end_date
        else:
            start_date_str = start_date
            end_date_str = end_date
        
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Datas devem estar no formato YYYY-MM-DD")
        
        if start_date_obj > end_date_obj:
            raise HTTPException(status_code=400, detail="Data de início deve ser anterior ou igual à data de fim")
        
        period_start = datetime.combine(start_date_obj, datetime.min.time())
        period_end = datetime.combine(end_date_obj, datetime.max.time())
        
        from app.models.debtor import Debtor, DebtorStatus
        
        # Inicializar contadores
        income_cash = Decimal('0.00')
        income_bank = Decimal('0.00')
        expenses_cash = Decimal('0.00')
        expenses_bank = Decimal('0.00')
        methods_detailed_map = {
            'pix': Decimal('0.00'),
            'credit_card': Decimal('0.00'),
            'debit_card': Decimal('0.00'),
            'cash': Decimal('0.00'),
            'bank_transfer': Decimal('0.00')
        }
        
        # Buscar PaymentEntry de transações pagas imediatamente no período
        payment_entries_immediate_query = select(PaymentEntry).join(
            Transaction, PaymentEntry.transaction_id == Transaction.id
        ).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start,
                Transaction.date_time <= period_end,
                Transaction.is_paid == True  # Apenas pagas (não inclui PENDING)
            )
        )
        payment_entries_immediate_result = await db.execute(payment_entries_immediate_query)
        payment_entries_immediate = payment_entries_immediate_result.scalars().all()
        
        # Buscar PaymentEntry de contas a receber BAIXADAS no período (usando Debtor.paid_at)
        # IMPORTANTE: Apenas status PAID, nunca PENDING
        debtors_paid_query = select(Debtor).join(
            Transaction, Debtor.transaction_id == Transaction.id
        ).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Debtor.status == DebtorStatus.PAID,  # Apenas pagas
                Debtor.paid_at >= period_start,
                Debtor.paid_at <= period_end
            )
        )
        debtors_paid_result = await db.execute(debtors_paid_query)
        debtors_paid = debtors_paid_result.scalars().all()
        
        debtor_transaction_ids = [str(d.transaction_id) for d in debtors_paid]
        payment_entries_settled = []
        if debtor_transaction_ids:
            payment_entries_settled_query = select(PaymentEntry).where(
                PaymentEntry.transaction_id.in_(debtor_transaction_ids)
            )
            payment_entries_settled_result = await db.execute(payment_entries_settled_query)
            payment_entries_settled = payment_entries_settled_result.scalars().all()
        
        # Criar mapa de transações para verificar data de pagamento
        transaction_ids_set = set([pe.transaction_id for pe in payment_entries_immediate] + [str(d.transaction_id) for d in debtors_paid])
        transactions_query = select(Transaction).where(
            Transaction.id.in_(list(transaction_ids_set))
        )
        transactions_result = await db.execute(transactions_query)
        transactions_list = transactions_result.scalars().all()
        transactions_map = {str(t.id): t for t in transactions_list}
        debtor_paid_at_map = {str(d.transaction_id): d.paid_at for d in debtors_paid if d.paid_at}
        
        # Combinar todos os PaymentEntry e filtrar pelo período correto
        all_payment_entries = []
        
        # Processar PaymentEntry imediatos (já filtrados por transaction.date_time no período)
        for pe in payment_entries_immediate:
            transaction = transactions_map.get(pe.transaction_id)
            if transaction:
                # Já está filtrado, mas vamos garantir que transaction.date_time está no período
                if period_start <= transaction.date_time <= period_end:
                    all_payment_entries.append(pe)
        
        # Processar PaymentEntry de contas a receber baixadas
        for pe in payment_entries_settled:
            transaction_id = pe.transaction_id
            # Verificar se paid_at está no período
            paid_at = debtor_paid_at_map.get(transaction_id)
            if paid_at and period_start <= paid_at <= period_end:
                all_payment_entries.append(pe)
        
        # Processar entradas (receitas)
        for pe in all_payment_entries:
            payment_method_query = select(PaymentMethodConfig).where(
                PaymentMethodConfig.id == str(pe.payment_method_id)
            )
            payment_method_result = await db.execute(payment_method_query)
            payment_method = payment_method_result.scalar_one_or_none()
            
            if payment_method:
                value = Decimal(str(pe.value_paid))
                method_name = payment_method.method_name
                
                # Classificar como CASH ou BANCO baseado no método efetivo usado
                if is_cash_payment_method(method_name):
                    income_cash += value
                else:
                    income_bank += value
                
                # Adicionar ao detalhamento por método
                detailed_key = get_payment_method_detailed_key(method_name)
                if detailed_key and detailed_key in methods_detailed_map:
                    methods_detailed_map[detailed_key] += value
        
        # Buscar e processar despesas
        expenses_query = select(Expense).where(
            and_(
                Expense.tenant_id == tenant_id_str,
                Expense.payment_date >= period_start,
                Expense.payment_date <= period_end
            )
        )
        expenses_result = await db.execute(expenses_query)
        expenses = expenses_result.scalars().all()
        
        for expense in expenses:
            expense_amount = Decimal(str(expense.amount))
            expense_category = get_expense_payment_category(expense.payment_method)
            
            if expense_category == 'CASH':
                expenses_cash += expense_amount
            else:
                expenses_bank += expense_amount
        
        # Calcular saldos líquidos
        net_cash = income_cash - expenses_cash
        net_bank = income_bank - expenses_bank
        
        # Calcular totais gerais
        gross_total = income_cash + income_bank
        net_total = net_cash + net_bank
        
        # Determinar tipo de período
        is_daily = start_date_obj == end_date_obj
        period_type = 'daily' if is_daily else 'custom'
        
        return DetailedCashSummaryResponse(
            general=GeneralSummary(
                gross_total=gross_total,
                net_total=net_total
            ),
            breakdown=BreakdownSummary(
                physical_cash=BreakdownCategory(
                    income=income_cash,
                    expenses=expenses_cash,
                    balance=net_cash
                ),
                bank_digital=BreakdownCategory(
                    income=income_bank,
                    expenses=expenses_bank,
                    balance=net_bank
                )
            ),
            methods_detailed=MethodsDetailed(
                pix=methods_detailed_map['pix'],
                credit_card=methods_detailed_map['credit_card'],
                debit_card=methods_detailed_map['debit_card'],
                cash=methods_detailed_map['cash'],
                bank_transfer=methods_detailed_map['bank_transfer']
            ),
            period_start=period_start,
            period_end=period_end,
            period_type=period_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao calcular resumo detalhado do caixa: {str(e)}"
        )


@router.get(
    "/cash-summary",
    response_model=dict,
    summary="Resumo do Caixa",
    description="Retorna resumo financeiro do caixa para um período personalizado ou diário padrão."
)
async def get_cash_summary(
    start_date: Optional[str] = Query(None, description="Data de início no formato YYYY-MM-DD. Se não fornecido, usa hoje."),
    end_date: Optional[str] = Query(None, description="Data de fim no formato YYYY-MM-DD. Se não fornecido, usa hoje."),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna resumo do caixa para um período específico.
    
    Calcula:
    - Faturamento bruto e líquido
    - Custos totais (serviços + adicional)
    - Lucro total
    - Despesas totais
    - Resumo por forma de pagamento
    
    Args:
        start_date: Data de início no formato YYYY-MM-DD (opcional, padrão: hoje)
        end_date: Data de fim no formato YYYY-MM-DD (opcional, padrão: hoje)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        dict: Resumo do caixa para o período especificado
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(status_code=400, detail="tenant_id inválido")
        
        # Determinar período
        today = datetime.now().date()
        
        # Se nenhum parâmetro for fornecido, usar dia atual (caixa diário padrão)
        if not start_date and not end_date:
            start_date_str = today.strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif start_date and not end_date:
            # Se apenas start_date for fornecido, usar o mesmo dia
            end_date_str = start_date
            start_date_str = start_date
        elif not start_date and end_date:
            # Se apenas end_date for fornecido, usar o mesmo dia
            start_date_str = end_date
            end_date_str = end_date
        else:
            # Ambos fornecidos
            start_date_str = start_date
            end_date_str = end_date
        
        # Validar e converter datas
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Datas devem estar no formato YYYY-MM-DD")
        
        # Validar que start_date <= end_date
        if start_date_obj > end_date_obj:
            raise HTTPException(status_code=400, detail="Data de início deve ser anterior ou igual à data de fim")
        
        # Criar períodos datetime UTC (timezone-naive para compatibilidade com PostgreSQL)
        # O PostgreSQL armazena como TIMESTAMP WITHOUT TIME ZONE, então não podemos usar timezone-aware
        period_start = datetime.combine(start_date_obj, datetime.min.time())
        period_end = datetime.combine(end_date_obj, datetime.max.time())
        
        # Função auxiliar para calcular resumo de um período
        async def calculate_summary(start_dt, end_dt):
            # NOVA LÓGICA: Buscar PaymentEntry que devem entrar no caixa do período
            # 1. PaymentEntry de transações com date_time no período (pagamentos imediatos)
            # 2. PaymentEntry de contas a receber baixadas no período (usando Debtor.paid_at)
            from app.models.debtor import Debtor, DebtorStatus
            
            # Buscar PaymentEntry de transações com date_time no período (pagamentos imediatos)
            payment_entries_immediate_query = select(PaymentEntry).join(
                Transaction, PaymentEntry.transaction_id == Transaction.id
            ).where(
                and_(
                    Transaction.tenant_id == tenant_id_str,
                    Transaction.date_time >= start_dt,
                    Transaction.date_time <= end_dt,
                    Transaction.is_paid == True
                )
            )
            payment_entries_immediate_result = await db.execute(payment_entries_immediate_query)
            payment_entries_immediate = payment_entries_immediate_result.scalars().all()
            
            # Buscar PaymentEntry de contas a receber baixadas no período
            # (usando Debtor.paid_at para determinar quando foi pago)
            debtors_paid_query = select(Debtor).join(
                Transaction, Debtor.transaction_id == Transaction.id
            ).where(
                and_(
                    Transaction.tenant_id == tenant_id_str,
                    Debtor.status == DebtorStatus.PAID,
                    Debtor.paid_at >= start_dt,
                    Debtor.paid_at <= end_dt
                )
            )
            debtors_paid_result = await db.execute(debtors_paid_query)
            debtors_paid = debtors_paid_result.scalars().all()
            
            # Obter transaction_ids das contas a receber baixadas
            debtor_transaction_ids = [str(d.transaction_id) for d in debtors_paid]
            
            # Buscar PaymentEntry dessas transações (criados quando a conta foi baixada)
            payment_entries_settled = []
            if debtor_transaction_ids:
                payment_entries_settled_query = select(PaymentEntry).where(
                    PaymentEntry.transaction_id.in_(debtor_transaction_ids)
                )
                payment_entries_settled_result = await db.execute(payment_entries_settled_query)
                payment_entries_settled = payment_entries_settled_result.scalars().all()
            
            # Combinar todos os PaymentEntry do período
            payment_entries = list(payment_entries_immediate) + list(payment_entries_settled)
            
            # Obter transaction_ids únicos
            transaction_ids = list(set([pe.transaction_id for pe in payment_entries]))
            
            # Buscar despesas mesmo se não há transações
            expenses_query = select(Expense).where(
                and_(
                    Expense.tenant_id == tenant_id_str,
                    Expense.payment_date >= start_dt,
                    Expense.payment_date <= end_dt
                )
            )
            expenses_result = await db.execute(expenses_query)
            expenses = expenses_result.scalars().all()
            
            # Buscar métodos de pagamento para mapear despesas
            payment_methods_config_query = select(PaymentMethodConfig).where(
                PaymentMethodConfig.tenant_id == tenant_id_str
            )
            payment_methods_config_result = await db.execute(payment_methods_config_query)
            payment_methods_config = payment_methods_config_result.scalars().all()
            
            # Criar mapa de nomes normalizados
            method_name_map = {}
            for pmc in payment_methods_config:
                method_name_lower = pmc.method_name.lower().strip()
                if 'dinheiro' in method_name_lower or 'cash' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.CASH] = pmc.method_name
                elif 'pix' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.PIX] = pmc.method_name
                elif 'crédito' in method_name_lower or 'credit' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.CREDIT_CARD] = pmc.method_name
                elif 'débito' in method_name_lower or 'debit' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.DEBIT_CARD] = pmc.method_name
                elif 'transferência' in method_name_lower or 'transfer' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.BANK_TRANSFER] = pmc.method_name
            
            expenses_by_method = {}
            for expense in expenses:
                expense_amount = Decimal(str(expense.amount))
                expense_method_name = method_name_map.get(expense.payment_method, None)
                if expense_method_name:
                    if expense_method_name not in expenses_by_method:
                        expenses_by_method[expense_method_name] = Decimal('0.00')
                    expenses_by_method[expense_method_name] += expense_amount
            
            total_expenses = sum(expenses_by_method.values()) if expenses_by_method else Decimal('0.00')
            
            # Criar payment_methods_summary mesmo sem receitas (apenas despesas)
            payment_methods_summary = []
            for method_name, expense_amount in expenses_by_method.items():
                pmc_query = select(PaymentMethodConfig).where(
                    and_(
                        PaymentMethodConfig.tenant_id == tenant_id_str,
                        PaymentMethodConfig.method_name == method_name
                    )
                )
                pmc_result = await db.execute(pmc_query)
                pmc = pmc_result.scalar_one_or_none()
                is_bank = False
                if pmc:
                    method_lower = pmc.method_name.lower()
                    is_bank = any(x in method_lower for x in ['pix', 'cartão', 'card', 'transfer', 'transferência'])
                
                payment_methods_summary.append(
                    PaymentMethodSummary(
                        method_name=method_name,
                        total_received=Decimal('0.00'),
                        total_expenses=expense_amount,
                        net_balance=Decimal('0.00') - expense_amount,  # Saldo negativo (só despesas)
                        is_bank_account=is_bank
                    )
                )
            
            if not transaction_ids:
                # Se não há PaymentEntry no período, retornar zeros mas com despesas se houver
                return {
                    'period_start': start_dt,
                    'period_end': end_dt,
                    'gross_revenue': Decimal('0.00'),
                    'net_revenue': Decimal('0.00'),
                    'total_service_cost': Decimal('0.00'),
                    'total_additional_cost': Decimal('0.00'),
                    'total_cost': Decimal('0.00'),
                    'total_profit': Decimal('0.00'),
                    'total_expenses': total_expenses,
                    'net_balance': Decimal('0.00') - total_expenses,
                    'payment_methods_summary': payment_methods_summary,
                    'total_transactions': 0,
                    'total_appointments': 0
                }
            
            # Buscar transações relacionadas aos PaymentEntry
            transactions_query = select(Transaction).where(
                Transaction.id.in_(transaction_ids)
            )
            transactions_result = await db.execute(transactions_query)
            transactions = transactions_result.scalars().all()
            
            # Criar mapa de transações para acesso rápido
            transactions_map = {str(t.id): t for t in transactions}
            
            # Criar mapa de Debtor.paid_at por transaction_id para determinar data de pagamento
            debtor_paid_at_map = {str(d.transaction_id): d.paid_at for d in debtors_paid if d.paid_at}
            
            # Calcular totais
            gross_revenue = Decimal('0.00')
            net_revenue = Decimal('0.00')
            total_service_cost = Decimal('0.00')
            total_additional_cost = Decimal('0.00')
            total_profit = Decimal('0.00')
            total_transactions = len(set(transaction_ids))
            
            # Resumo por forma de pagamento
            payment_methods_map = {}
            
            # Inicializar despesas por método de pagamento (todas começam com 0)
            expenses_by_method = {}
            
            # Buscar todas as despesas do período
            expenses_query = select(Expense).where(
                and_(
                    Expense.tenant_id == tenant_id_str,
                    Expense.payment_date >= start_dt,
                    Expense.payment_date <= end_dt
                )
            )
            expenses_result = await db.execute(expenses_query)
            expenses = expenses_result.scalars().all()
            
            # Mapear PaymentMethodEnum para nomes de métodos de pagamento comuns
            # Buscar todos os métodos de pagamento do tenant para fazer match
            payment_methods_config_query = select(PaymentMethodConfig).where(
                PaymentMethodConfig.tenant_id == tenant_id_str
            )
            payment_methods_config_result = await db.execute(payment_methods_config_query)
            payment_methods_config = payment_methods_config_result.scalars().all()
            
            # Criar mapa de nomes normalizados para PaymentMethodConfig
            method_name_map = {}
            for pmc in payment_methods_config:
                method_name_lower = pmc.method_name.lower().strip()
                # Normalizar nomes comuns
                if 'dinheiro' in method_name_lower or 'cash' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.CASH] = pmc.method_name
                elif 'pix' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.PIX] = pmc.method_name
                elif 'crédito' in method_name_lower or 'credit' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.CREDIT_CARD] = pmc.method_name
                elif 'débito' in method_name_lower or 'debit' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.DEBIT_CARD] = pmc.method_name
                elif 'transferência' in method_name_lower or 'transfer' in method_name_lower:
                    method_name_map[ExpensePaymentMethodEnum.BANK_TRANSFER] = pmc.method_name
            
            # Agrupar despesas por método de pagamento
            for expense in expenses:
                expense_amount = Decimal(str(expense.amount))
                expense_method_name = method_name_map.get(expense.payment_method, None)
                
                if expense_method_name:
                    if expense_method_name not in expenses_by_method:
                        expenses_by_method[expense_method_name] = Decimal('0.00')
                    expenses_by_method[expense_method_name] += expense_amount
            
            # Agrupar PaymentEntry por transaction_id para calcular proporções corretas
            payment_entries_by_transaction = {}
            for pe in payment_entries:
                if pe.transaction_id not in payment_entries_by_transaction:
                    payment_entries_by_transaction[pe.transaction_id] = []
                payment_entries_by_transaction[pe.transaction_id].append(pe)
            
            for transaction_id, payment_entries_list in payment_entries_by_transaction.items():
                transaction = transactions_map.get(transaction_id)
                if not transaction:
                    continue
                
                # Determinar se este PaymentEntry deve entrar no período
                # Se é de uma conta a receber baixada, usar paid_at
                # Se é pagamento imediato, usar transaction.date_time
                is_settled_debtor = transaction_id in debtor_paid_at_map
                
                # Filtrar PaymentEntry que devem entrar no período
                payment_entries_in_period = []
                for pe in payment_entries_list:
                    if is_settled_debtor:
                        # Se é conta a receber baixada, verificar se paid_at está no período
                        paid_at = debtor_paid_at_map.get(transaction_id)
                        if paid_at and start_dt <= paid_at <= end_dt:
                            payment_entries_in_period.append(pe)
                    else:
                        # Se é pagamento imediato, verificar se transaction.date_time está no período
                        if start_dt <= transaction.date_time <= end_dt:
                            payment_entries_in_period.append(pe)
                
                if not payment_entries_in_period:
                    continue
                
                # Calcular total pago no período
                total_paid_in_period = Decimal('0.00')
                
                for pe in payment_entries_in_period:
                    # Somar apenas valores pagos no período
                    total_paid_in_period += Decimal(str(pe.value_paid))
                    
                    # Buscar nome da forma de pagamento
                    payment_method_query = select(PaymentMethodConfig).where(
                        PaymentMethodConfig.id == str(pe.payment_method_id)
                    )
                    payment_method_result = await db.execute(payment_method_query)
                    payment_method = payment_method_result.scalar_one_or_none()
                    
                    if payment_method:
                        method_name = payment_method.method_name
                        if method_name not in payment_methods_map:
                            payment_methods_map[method_name] = {
                                'total_received': Decimal('0.00'),
                                'is_bank_account': pe.is_bank_account
                            }
                        payment_methods_map[method_name]['total_received'] += Decimal(str(pe.value_paid))
                
                # Calcular valor final após desconto (usado para proporções)
                discount_value = Decimal(str(transaction.discount)) if transaction.discount else Decimal('0.00')
                final_value_after_discount = transaction.gross_value - discount_value
                
                # REGRA: Se product_cost ou service_cost estão zerados/nulos, líquido = bruto
                has_cost = False
                service_cost_value = Decimal('0.00')
                additional_cost_value = Decimal(str(transaction.additional_cost)) if transaction.additional_cost else Decimal('0.00')
                
                if transaction.appointment_id:
                    appointment_query = select(Appointment).where(
                        Appointment.id == str(transaction.appointment_id)
                    )
                    appointment_result = await db.execute(appointment_query)
                    appointment = appointment_result.scalar_one_or_none()
                    if appointment and appointment.service_cost:
                        service_cost_value = Decimal(str(appointment.service_cost))
                        has_cost = True
                
                if transaction.additional_cost:
                    has_cost = True
                
                # Calcular proporção do valor pago no período
                if final_value_after_discount > Decimal('0.00'):
                    paid_proportion = total_paid_in_period / final_value_after_discount
                else:
                    paid_proportion = Decimal('1.00') if total_paid_in_period > Decimal('0.00') else Decimal('0.00')
                
                # REGRA: Se não há custos, líquido = bruto
                if not has_cost or (service_cost_value == Decimal('0.00') and additional_cost_value == Decimal('0.00')):
                    # Líquido = Bruto (sem descontar custos)
                    gross_revenue += total_paid_in_period
                    net_revenue += total_paid_in_period
                    # Lucro = Líquido (já que não há custos)
                    total_profit += total_paid_in_period
                else:
                    # Calcular valores proporcionais
                    gross_revenue += total_paid_in_period
                    net_revenue += transaction.net_value * paid_proportion
                    total_profit += transaction.total_profit * paid_proportion
                    
                    # Calcular custos proporcionais
                    if service_cost_value > Decimal('0.00'):
                        total_service_cost += service_cost_value * paid_proportion
                    if additional_cost_value > Decimal('0.00'):
                        total_additional_cost += additional_cost_value * paid_proportion
            
            total_cost = total_service_cost + total_additional_cost
            
            # Adicionar despesas ao mapa de métodos de pagamento
            # Inicializar métodos que têm despesas mas não têm receitas
            for method_name, expense_amount in expenses_by_method.items():
                if method_name not in payment_methods_map:
                    # Buscar PaymentMethodConfig para determinar se é conta bancária
                    pmc_query = select(PaymentMethodConfig).where(
                        and_(
                            PaymentMethodConfig.tenant_id == tenant_id_str,
                            PaymentMethodConfig.method_name == method_name
                        )
                    )
                    pmc_result = await db.execute(pmc_query)
                    pmc = pmc_result.scalar_one_or_none()
                    is_bank = False
                    if pmc:
                        # Considerar conta bancária se for PIX, Cartão ou Transferência
                        method_lower = pmc.method_name.lower()
                        is_bank = any(x in method_lower for x in ['pix', 'cartão', 'card', 'transfer', 'transferência'])
                    
                    payment_methods_map[method_name] = {
                        'total_received': Decimal('0.00'),
                        'is_bank_account': is_bank
                    }
            
            # Converter resumo de formas de pagamento incluindo despesas
            payment_methods_summary = []
            for name, data in payment_methods_map.items():
                total_received = data['total_received']
                total_expenses_for_method = expenses_by_method.get(name, Decimal('0.00'))
                net_balance = total_received - total_expenses_for_method
                
                payment_methods_summary.append(
                    PaymentMethodSummary(
                        method_name=name,
                        total_received=total_received,
                        total_expenses=total_expenses_for_method,
                        net_balance=net_balance,
                        is_bank_account=data['is_bank_account']
                    )
                )
            
            # Contar agendamentos finalizados
            appointments_query = select(func.count(Appointment.id)).where(
                and_(
                    Appointment.tenant_id == tenant_id_str,
                    Appointment.status == 'COMPLETED',
                    Appointment.start_datetime >= start_dt,
                    Appointment.start_datetime <= end_dt
                )
            )
            appointments_result = await db.execute(appointments_query)
            total_appointments = appointments_result.scalar() or 0
            
            # Calcular despesas totais do período
            total_expenses = sum(expenses_by_method.values()) if expenses_by_method else Decimal('0.00')
            
            # Calcular saldo líquido geral
            net_balance = net_revenue - total_expenses
            
            return {
                'period_start': start_dt,
                'period_end': end_dt,
                'gross_revenue': gross_revenue,
                'net_revenue': net_revenue,
                'total_service_cost': total_service_cost,
                'total_additional_cost': total_additional_cost,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'total_expenses': total_expenses,
                'net_balance': net_balance,
                'payment_methods_summary': payment_methods_summary,
                'total_transactions': total_transactions,
                'total_appointments': total_appointments
            }
        
        # Calcular resumo do período especificado
        period_summary = await calculate_summary(period_start, period_end)
        
        # Determinar se é diário ou período personalizado
        is_daily = start_date_obj == end_date_obj
        period_type = 'daily' if is_daily else 'custom'
        
        return {
            'summary': CashSummaryResponse(**period_summary, period_type=period_type),
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'is_daily': is_daily
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao calcular resumo do caixa: {str(e)}"
        )


@router.get(
    "/transactions",
    response_model=TransactionsListResponse,
    summary="Listar Transações",
    description="Lista transações detalhadas com filtros opcionais."
)
async def list_transactions(
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    customer_name: Optional[str] = Query(None, description="Filtrar por nome do cliente"),
    payment_method_id: Optional[UUID] = Query(None, description="Filtrar por forma de pagamento"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista transações detalhadas com filtros opcionais.
    
    Args:
        start_date: Data inicial para filtrar (YYYY-MM-DD)
        end_date: Data final para filtrar (YYYY-MM-DD)
        customer_name: Nome do cliente para filtrar (busca parcial)
        payment_method_id: ID da forma de pagamento para filtrar
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        TransactionsListResponse: Lista de transações com detalhes
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(status_code=400, detail="tenant_id inválido")
        
        # Construir query base
        query = select(Transaction).where(
            Transaction.tenant_id == tenant_id_str
        )
        
        # Aplicar filtros
        period_start = None
        period_end = None
        
        if start_date:
            try:
                period_start = datetime.strptime(start_date, '%Y-%m-%d').replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                query = query.where(Transaction.date_time >= period_start)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_date deve estar no formato YYYY-MM-DD")
        
        if end_date:
            try:
                period_end = datetime.strptime(end_date, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                query = query.where(Transaction.date_time <= period_end)
            except ValueError:
                raise HTTPException(status_code=400, detail="end_date deve estar no formato YYYY-MM-DD")
        
        # Filtrar por forma de pagamento (via PaymentEntry)
        if payment_method_id:
            payment_method_id_str = str(payment_method_id)
            # Buscar transaction_ids que têm esta forma de pagamento
            payment_entries_query = select(PaymentEntry.transaction_id).where(
                PaymentEntry.payment_method_id == payment_method_id_str
            )
            payment_entries_result = await db.execute(payment_entries_query)
            transaction_ids = [str(row[0]) for row in payment_entries_result.fetchall()]
            
            if transaction_ids:
                query = query.where(Transaction.id.in_(transaction_ids))
            else:
                # Se não houver transações com esta forma de pagamento, retornar vazio
                return TransactionsListResponse(
                    transactions=[],
                    total_count=0,
                    period_start=period_start,
                    period_end=period_end
                )
        
        # Ordenar por data (mais recente primeiro)
        query = query.order_by(Transaction.date_time.desc())
        
        # Executar query
        transactions_result = await db.execute(query)
        transactions = transactions_result.scalars().all()
        
        # Filtrar por nome do cliente (se fornecido) e construir resposta detalhada
        transaction_details = []
        
        for transaction in transactions:
            # Buscar appointment para obter dados do cliente
            appointment_query = select(Appointment).where(
                Appointment.id == str(transaction.appointment_id)
            )
            appointment_result = await db.execute(appointment_query)
            appointment = appointment_result.scalar_one_or_none()
            
            if not appointment:
                continue
            
            # Filtrar por nome do cliente (busca parcial, case-insensitive)
            if customer_name:
                if not appointment.customer_name or \
                   customer_name.lower() not in appointment.customer_name.lower():
                    continue
            
            # Buscar nome do serviço
            service_name = None
            if appointment.service_id:
                service_query = select(Service).where(Service.id == str(appointment.service_id))
                service_result = await db.execute(service_query)
                service = service_result.scalar_one_or_none()
                if service:
                    service_name = service.name
            
            # Buscar payment entries
            payment_entries_query = select(PaymentEntry).where(
                PaymentEntry.transaction_id == str(transaction.id)
            )
            payment_entries_result = await db.execute(payment_entries_query)
            payment_entries = payment_entries_result.scalars().all()
            
            payment_entry_details = []
            for pe in payment_entries:
                # Buscar nome da forma de pagamento
                payment_method_query = select(PaymentMethodConfig).where(
                    PaymentMethodConfig.id == str(pe.payment_method_id)
                )
                payment_method_result = await db.execute(payment_method_query)
                payment_method = payment_method_result.scalar_one_or_none()
                
                payment_entry_details.append(
                    PaymentEntryDetail(
                        id=UUID(str(pe.id)),
                        payment_method_name=payment_method.method_name if payment_method else 'Desconhecido',
                        value_paid=pe.value_paid,
                        installments=pe.installments,
                        is_bank_account=pe.is_bank_account
                    )
                )
            
            transaction_details.append(
                TransactionDetailResponse(
                    id=UUID(str(transaction.id)),
                    appointment_id=UUID(str(transaction.appointment_id)),
                    customer_name=appointment.customer_name,
                    customer_phone=appointment.customer_phone,
                    service_name=service_name,
                    date_time=transaction.date_time,
                    gross_value=transaction.gross_value,
                    net_value=transaction.net_value,
                    total_cost=transaction.total_cost,
                    total_profit=transaction.total_profit,
                    additional_cost=transaction.additional_cost,
                    payment_entries=payment_entry_details
                )
            )
        
        return TransactionsListResponse(
            transactions=transaction_details,
            total_count=len(transaction_details),
            period_start=period_start,
            period_end=period_end
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar transações: {str(e)}"
        )


@router.get(
    "/birthdays",
    response_model=List[BirthdayClientResponse],
    summary="Aniversariantes do mês",
    description="Retorna os clientes aniversariantes do mês atual, filtrados pelo tenant_id."
)
async def get_birthdays(
    month: Optional[int] = Query(None, description="Mês (1-12). Se não fornecido, usa o mês atual."),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna os clientes aniversariantes do mês especificado (ou mês atual).
    
    Args:
        month: Mês (1-12). Se não fornecido, usa o mês atual.
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[BirthdayClientResponse]: Lista de clientes aniversariantes ordenados por dia do mês
    """
    try:
        tenant_id_str = str(tenant.id)
        
        # Usar mês atual se não fornecido
        if month is None:
            month = datetime.now().month
        else:
            if month < 1 or month > 12:
                raise HTTPException(
                    status_code=400,
                    detail="Mês deve estar entre 1 e 12"
                )
        
        # Buscar clientes com aniversário no mês especificado
        # PostgreSQL usa func.extract() para extrair mês e dia
        query = select(Client).where(
            and_(
                Client.tenant_id == tenant_id_str,
                Client.birth_date.isnot(None),
                func.extract('month', Client.birth_date) == month
            )
        ).order_by(func.extract('day', Client.birth_date))  # Ordenar por dia do mês
        
        result = await db.execute(query)
        clients = result.scalars().all()
        
        # Converter para resposta com dia do mês
        birthday_clients = []
        for client in clients:
            if client.birth_date:
                birthday_clients.append(
                    BirthdayClientResponse(
                        id=UUID(str(client.id)),
                        name=client.name,
                        phone_number=client.phone_number,
                        email=client.email,
                        birth_date=client.birth_date,
                        day_of_month=client.birth_date.day
                    )
                )
        
        return birthday_clients
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar aniversariantes: {str(e)}"
        )

