"""
Endpoints administrativos para Relatórios e Caixa.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from uuid import UUID
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.transaction import Transaction
from app.models.payment_entry import PaymentEntry
from app.models.payment_method_config import PaymentMethodConfig
from app.models.appointment import Appointment
from app.models.service import Service
from app.models.expense import Expense
from app.models.client import Client

from app.schemas.report import (
    CashSummaryResponse,
    PaymentMethodSummary,
    TransactionDetailResponse,
    PaymentEntryDetail,
    TransactionsListResponse
)
from app.schemas.client import BirthdayClientResponse

router = APIRouter(prefix="/admin/reports", tags=["Admin - Reports"])


@router.get(
    "/cash-summary",
    response_model=dict,
    summary="Resumo do Caixa",
    description="Retorna resumo financeiro do caixa para um período personalizado ou diário padrão."
)
async def get_cash_summary(
    start_date: Optional[str] = Query(None, description="Data de início no formato YYYY-MM-DD. Se não fornecido, usa hoje."),
    end_date: Optional[str] = Query(None, description="Data de fim no formato YYYY-MM-DD. Se não fornecido, usa hoje."),
    tenant: Tenant = Depends(get_current_active_tenant),
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
            # Buscar transações do período (apenas as pagas, pois as não pagas não entram no caixa ainda)
            transactions_query = select(Transaction).where(
                and_(
                    Transaction.tenant_id == tenant_id_str,
                    Transaction.date_time >= start_dt,
                    Transaction.date_time <= end_dt,
                    Transaction.is_paid == True  # Apenas transações pagas entram no caixa
                )
            )
            transactions_result = await db.execute(transactions_query)
            transactions = transactions_result.scalars().all()
            
            # Calcular totais
            gross_revenue = Decimal('0.00')
            net_revenue = Decimal('0.00')
            total_service_cost = Decimal('0.00')
            total_additional_cost = Decimal('0.00')
            total_profit = Decimal('0.00')
            total_transactions = len(transactions)
            
            # Resumo por forma de pagamento
            payment_methods_map = {}
            
            for transaction in transactions:
                gross_revenue += Decimal(str(transaction.gross_value))
                net_revenue += Decimal(str(transaction.net_value))
                total_profit += Decimal(str(transaction.total_profit))
                
                # Calcular custo (sem additional_cost duplicado)
                # total_cost já inclui additional_cost, então precisamos separar
                # Vamos usar uma query para buscar o custo do serviço do appointment
                if transaction.appointment_id:
                    appointment_query = select(Appointment).where(
                        Appointment.id == str(transaction.appointment_id)
                    )
                    appointment_result = await db.execute(appointment_query)
                    appointment = appointment_result.scalar_one_or_none()
                    if appointment and appointment.service_cost:
                        total_service_cost += Decimal(str(appointment.service_cost))
                
                if transaction.additional_cost:
                    total_additional_cost += Decimal(str(transaction.additional_cost))
                
                # Buscar payment entries desta transação
                payment_entries_query = select(PaymentEntry).where(
                    PaymentEntry.transaction_id == str(transaction.id)
                )
                payment_entries_result = await db.execute(payment_entries_query)
                payment_entries = payment_entries_result.scalars().all()
                
                for pe in payment_entries:
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
            
            total_cost = total_service_cost + total_additional_cost
            
            # Converter resumo de formas de pagamento
            payment_methods_summary = [
                PaymentMethodSummary(
                    method_name=name,
                    total_received=data['total_received'],
                    is_bank_account=data['is_bank_account']
                )
                for name, data in payment_methods_map.items()
            ]
            
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
            expenses_query = select(func.sum(Expense.value)).where(
                and_(
                    Expense.tenant_id == tenant_id_str,
                    Expense.date_time >= start_dt,
                    Expense.date_time <= end_dt
                )
            )
            expenses_result = await db.execute(expenses_query)
            total_expenses = expenses_result.scalar() or Decimal('0.00')
            
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
    tenant: Tenant = Depends(get_current_active_tenant),
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
    tenant: Tenant = Depends(get_current_active_tenant),
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
        # MySQL usa func.month() em vez de extract('month', ...)
        query = select(Client).where(
            and_(
                Client.tenant_id == tenant_id_str,
                Client.birth_date.isnot(None),
                func.month(Client.birth_date) == month
            )
        ).order_by(func.day(Client.birth_date))  # Ordenar por dia do mês
        
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

