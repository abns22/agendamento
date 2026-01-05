"""
Endpoints administrativos para estatísticas do Dashboard.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import verify_subscription_access
from app.models.tenant import Tenant
from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from app.models.transaction import Transaction
from app.models.appointment_service import AppointmentService
from pydantic import BaseModel

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


class DashboardStatsResponse(BaseModel):
    """Estatísticas do dashboard."""
    appointments_today: int
    active_services: int
    pending_appointments: int


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Obter estatísticas do dashboard",
    description="Retorna estatísticas resumidas para o dashboard do tenant autenticado."
)
async def get_dashboard_stats(
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna estatísticas do dashboard:
    - Agendamentos de hoje
    - Serviços ativos
    - Agendamentos pendentes
    
    Args:
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        DashboardStatsResponse: Estatísticas do dashboard
    """
    # IMPORTANTE: Converter tenant_id para string (MySQL armazena UUIDs como String(36))
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        return DashboardStatsResponse(
            appointments_today=0,
            active_services=0,
            pending_appointments=0
        )
    
    # 1. Agendamentos de hoje
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    appointments_today_query = select(func.count(Appointment.id)).where(
        and_(
            Appointment.tenant_id == tenant_id_str,
            Appointment.start_datetime >= start_of_day,
            Appointment.start_datetime <= end_of_day,
            Appointment.status != AppointmentStatus.CANCELED
        )
    )
    appointments_today_result = await db.execute(appointments_today_query)
    appointments_today = appointments_today_result.scalar() or 0
    
    # 2. Serviços ativos (todos os serviços do tenant)
    active_services_query = select(func.count(Service.id)).where(
        Service.tenant_id == tenant_id_str
    )
    active_services_result = await db.execute(active_services_query)
    active_services = active_services_result.scalar() or 0
    
    # 3. Agendamentos pendentes (status PENDING)
    pending_appointments_query = select(func.count(Appointment.id)).where(
        and_(
            Appointment.tenant_id == tenant_id_str,
            Appointment.status == AppointmentStatus.PENDING
        )
    )
    pending_appointments_result = await db.execute(pending_appointments_query)
    pending_appointments = pending_appointments_result.scalar() or 0
    
    return DashboardStatsResponse(
        appointments_today=appointments_today,
        active_services=active_services,
        pending_appointments=pending_appointments
    )


class DashboardSummaryResponse(BaseModel):
    """Resumo financeiro do dashboard."""
    faturamento_total: Decimal = Decimal('0.00')
    ticket_medio: Decimal = Decimal('0.00')
    servico_mais_procurado_id: Optional[str] = None
    total_descontos: Decimal = Decimal('0.00')
    periodo_inicio: date
    periodo_fim: date
    total_appointments_finalizados: int = 0


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Obter resumo financeiro do dashboard",
    description="Retorna métricas financeiras resumidas para o período especificado (ou mês atual se não fornecido)."
)
async def get_dashboard_summary(
    start_date: Optional[str] = Query(
        None,
        description="Data de início no formato YYYY-MM-DD (opcional, padrão: primeiro dia do mês atual)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Data de fim no formato YYYY-MM-DD (opcional, padrão: último dia do mês atual)"
    ),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna resumo financeiro do dashboard:
    - Faturamento Total: Soma de net_value de transações com agendamentos finalizados (status COMPLETED)
    - Ticket Médio: Faturamento Total / Número de agendamentos finalizados
    - Serviço Mais Procurado: ID do serviço que mais aparece em appointment_services para agendamentos COMPLETED
    - Total de Descontos: Soma da coluna discount das transações no período
    
    Args:
        start_date: Data de início (opcional, padrão: primeiro dia do mês atual)
        end_date: Data de fim (opcional, padrão: último dia do mês atual)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        DashboardSummaryResponse: Resumo financeiro do período
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(status_code=400, detail="tenant_id inválido")
        
        # Definir período padrão (mês atual) se não fornecido
        today = date.today()
        if start_date:
            try:
                period_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail="start_date deve estar no formato YYYY-MM-DD")
        else:
            # Primeiro dia do mês atual
            period_start = date(today.year, today.month, 1)
        
        if end_date:
            try:
                period_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail="end_date deve estar no formato YYYY-MM-DD")
        else:
            # Último dia do mês atual
            if today.month == 12:
                period_end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        # Converter para datetime para comparação (início e fim do dia)
        period_start_dt = datetime.combine(period_start, datetime.min.time())
        period_end_dt = datetime.combine(period_end, datetime.max.time())
        
        # 1. FATURAMENTO TOTAL: Soma de net_value de transactions onde appointment.status = COMPLETED
        # Join Transaction -> Appointment para filtrar por status COMPLETED
        faturamento_query = select(func.coalesce(func.sum(Transaction.net_value), 0)).select_from(
            Transaction.__table__.join(
                Appointment.__table__,
                Transaction.appointment_id == Appointment.id
            )
        ).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt,
                Appointment.status == AppointmentStatus.COMPLETED
            )
        )
        faturamento_result = await db.execute(faturamento_query)
        faturamento_total = faturamento_result.scalar() or Decimal('0.00')
        
        # 2. TOTAL DE DESCONTOS: Soma de discount de transactions no período (com appointments COMPLETED)
        descontos_query = select(func.coalesce(func.sum(Transaction.discount), 0)).select_from(
            Transaction.__table__.join(
                Appointment.__table__,
                Transaction.appointment_id == Appointment.id
            )
        ).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt,
                Appointment.status == AppointmentStatus.COMPLETED
            )
        )
        descontos_result = await db.execute(descontos_query)
        total_descontos = descontos_result.scalar() or Decimal('0.00')
        
        # 3. TOTAL DE AGENDAMENTOS DO MÊS: Contar TODOS os appointments do período (exceto CANCELED)
        # Baseado na data do agendamento (start_datetime)
        # Isso inclui agendamentos manuais (SCHEDULED), agendamentos pelo booking (PENDING), 
        # agendamentos confirmados (CONFIRMED) e agendamentos finalizados (COMPLETED)
        # Exclui apenas bloqueios manuais (is_manual_block=True) e agendamentos cancelados
        appointments_mes_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.start_datetime >= period_start_dt,
                Appointment.start_datetime <= period_end_dt,
                Appointment.status != AppointmentStatus.CANCELED,
                Appointment.is_manual_block == False  # Excluir bloqueios manuais
            )
        )
        appointments_mes_result = await db.execute(appointments_mes_query)
        total_appointments_finalizados = appointments_mes_result.scalar() or 0
        
        # 4. CONTAR AGENDAMENTOS COM TRANSACTION (para ticket médio)
        # O ticket médio deve considerar apenas agendamentos que têm transaction (já que faturamento só considera esses)
        appointments_com_transaction_query = select(func.count(func.distinct(Transaction.appointment_id))).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt,
                Transaction.appointment_id.in_(
                    select(Appointment.id).where(
                        and_(
                            Appointment.tenant_id == tenant_id_str,
                            Appointment.status == AppointmentStatus.COMPLETED
                        )
                    )
                )
            )
        )
        appointments_com_transaction_result = await db.execute(appointments_com_transaction_query)
        total_appointments_com_transaction = appointments_com_transaction_result.scalar() or 0
        
        # 5. TICKET MÉDIO: Faturamento Total / Número de agendamentos com transaction
        ticket_medio = Decimal('0.00')
        if total_appointments_com_transaction > 0:
            ticket_medio = faturamento_total / Decimal(str(total_appointments_com_transaction))
        
        # 6. SERVIÇO MAIS PROCURADO: Contar ocorrências em appointment_services
        # Filtrando por appointments COMPLETED que têm transaction no período
        # Subquery para obter appointment_ids que têm transaction no período
        appointment_ids_subquery = select(Transaction.appointment_id).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt
            )
        )
        
        # Query para contar serviços mais procurados
        # Join AppointmentService -> Appointment
        count_alias = func.count(AppointmentService.service_id).label('count')
        servico_mais_procurado_query = select(
            AppointmentService.service_id,
            count_alias
        ).select_from(
            AppointmentService
        ).join(
            Appointment,
            AppointmentService.appointment_id == Appointment.id
        ).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.status == AppointmentStatus.COMPLETED,
                AppointmentService.appointment_id.in_(appointment_ids_subquery)
            )
        ).group_by(
            AppointmentService.service_id
        ).order_by(
            desc(count_alias)
        ).limit(1)
        
        servico_mais_procurado_result = await db.execute(servico_mais_procurado_query)
        servico_mais_procurado_row = servico_mais_procurado_result.first()
        servico_mais_procurado_id = str(servico_mais_procurado_row.service_id) if servico_mais_procurado_row else None
        
        return DashboardSummaryResponse(
            faturamento_total=faturamento_total,
            ticket_medio=ticket_medio,
            servico_mais_procurado_id=servico_mais_procurado_id,
            total_descontos=total_descontos,
            periodo_inicio=period_start,
            periodo_fim=period_end,
            total_appointments_finalizados=total_appointments_finalizados
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao calcular resumo financeiro: {str(e)}"
        )

