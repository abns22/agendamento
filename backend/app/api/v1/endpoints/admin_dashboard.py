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
from app.models.client import Client
from app.models.debtor import Debtor, DebtorStatus
from sqlalchemy.orm import selectinload
from typing import List
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
        # IMPORTANTE: Considerar apenas valores realmente recebidos:
        # - Transações com is_paid=True (pagas à vista)
        # - Contas a receber (is_paid=False) que foram pagas no período (Debtor.paid_at no período)
        
        # 1.1. Transações pagas à vista no período
        faturamento_paid_query = select(func.coalesce(func.sum(Transaction.net_value), 0)).select_from(
            Transaction.__table__.join(
                Appointment.__table__,
                Transaction.appointment_id == Appointment.id
            )
        ).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt,
                Transaction.is_paid == True,  # Apenas pagas
                Appointment.status == AppointmentStatus.COMPLETED
            )
        )
        faturamento_paid_result = await db.execute(faturamento_paid_query)
        faturamento_paid = faturamento_paid_result.scalar() or Decimal('0.00')
        
        # 1.2. Contas a receber que foram pagas no período (usando Debtor.paid_at)
        debtors_paid_query = select(Debtor).join(
            Transaction,
            Debtor.transaction_id == Transaction.id
        ).join(
            Appointment,
            Transaction.appointment_id == Appointment.id
        ).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Debtor.status == DebtorStatus.PAID,
                Debtor.paid_at >= period_start_dt,
                Debtor.paid_at <= period_end_dt,
                Appointment.status == AppointmentStatus.COMPLETED
            )
        )
        debtors_paid_result = await db.execute(debtors_paid_query)
        debtors_paid = debtors_paid_result.scalars().all()
        
        # Somar valores das contas a receber pagas no período
        faturamento_receivables = Decimal('0.00')
        for debtor in debtors_paid:
            faturamento_receivables += Decimal(str(debtor.value_due))
        
        # Faturamento total = pagas à vista + contas a receber pagas no período
        faturamento_total = faturamento_paid + faturamento_receivables
        
        # 2. TOTAL DE DESCONTOS: Soma de discount de transactions realmente recebidas no período
        # Considerar apenas transações pagas à vista (is_paid=True) e contas a receber pagas no período
        
        # 2.1. Descontos de transações pagas à vista
        descontos_paid_query = select(func.coalesce(func.sum(Transaction.discount), 0)).select_from(
            Transaction.__table__.join(
                Appointment.__table__,
                Transaction.appointment_id == Appointment.id
            )
        ).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt,
                Transaction.is_paid == True,  # Apenas pagas
                Appointment.status == AppointmentStatus.COMPLETED
            )
        )
        descontos_paid_result = await db.execute(descontos_paid_query)
        descontos_paid = descontos_paid_result.scalar() or Decimal('0.00')
        
        # 2.2. Descontos de contas a receber pagas no período
        # O desconto já está na Transaction, então precisamos buscar as transactions dos debtors pagos
        debtor_transaction_ids = [str(d.transaction_id) for d in debtors_paid]
        descontos_receivables = Decimal('0.00')
        if debtor_transaction_ids:
            descontos_receivables_query = select(func.coalesce(func.sum(Transaction.discount), 0)).where(
                and_(
                    Transaction.tenant_id == tenant_id_str,
                    Transaction.id.in_(debtor_transaction_ids)
                )
            )
            descontos_receivables_result = await db.execute(descontos_receivables_query)
            descontos_receivables = descontos_receivables_result.scalar() or Decimal('0.00')
        
        total_descontos = descontos_paid + descontos_receivables
        
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
        
        # 4. CONTAR AGENDAMENTOS COM TRANSACTION REALMENTE RECEBIDOS (para ticket médio)
        # Considerar apenas:
        # - Transações pagas à vista (is_paid=True) no período
        # - Contas a receber pagas no período (Debtor.paid_at no período)
        
        # 4.1. Agendamentos com transações pagas à vista no período
        appointments_paid_query = select(func.count(func.distinct(Transaction.appointment_id))).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt,
                Transaction.is_paid == True,  # Apenas pagas
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
        appointments_paid_result = await db.execute(appointments_paid_query)
        total_appointments_paid = appointments_paid_result.scalar() or 0
        
        # 4.2. Agendamentos com contas a receber pagas no período
        # Usar os debtors já buscados anteriormente
        debtor_appointment_ids = set()
        for debtor in debtors_paid:
            # Buscar appointment_id da transaction
            transaction_query = select(Transaction.appointment_id).where(
                Transaction.id == debtor.transaction_id
            )
            transaction_result = await db.execute(transaction_query)
            appointment_id = transaction_result.scalar_one_or_none()
            if appointment_id:
                debtor_appointment_ids.add(appointment_id)
        
        total_appointments_com_transaction = total_appointments_paid + len(debtor_appointment_ids)
        
        # 5. TICKET MÉDIO: Faturamento Total / Número de agendamentos com transaction
        ticket_medio = Decimal('0.00')
        if total_appointments_com_transaction > 0:
            ticket_medio = faturamento_total / Decimal(str(total_appointments_com_transaction))
        
        # 6. SERVIÇO MAIS PROCURADO: Contar ocorrências em appointment_services
        # Filtrando por appointments COMPLETED que têm transaction realmente recebida no período
        # Considerar apenas:
        # - Transações pagas à vista (is_paid=True) no período
        # - Contas a receber pagas no período (Debtor.paid_at no período)
        
        # 6.1. Appointment IDs de transações pagas à vista no período
        appointment_ids_paid_list = []
        appointments_paid_for_service_query = select(Transaction.appointment_id).where(
            and_(
                Transaction.tenant_id == tenant_id_str,
                Transaction.date_time >= period_start_dt,
                Transaction.date_time <= period_end_dt,
                Transaction.is_paid == True,  # Apenas pagas
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
        appointments_paid_for_service_result = await db.execute(appointments_paid_for_service_query)
        appointment_ids_paid_list = [apt_id for apt_id in appointments_paid_for_service_result.scalars().all()]
        
        # 6.2. Appointment IDs de contas a receber pagas no período (já temos em debtor_appointment_ids)
        # Combinar ambas as listas
        all_appointment_ids_received = set(appointment_ids_paid_list) | debtor_appointment_ids
        
        # Query para contar serviços mais procurados
        # Se não houver agendamentos recebidos, retornar None
        servico_mais_procurado_id = None
        if all_appointment_ids_received:
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
                    AppointmentService.appointment_id.in_(list(all_appointment_ids_received))
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


class UpcomingAppointmentItem(BaseModel):
    """Item de agendamento dentro de um dia."""
    id: str
    start_time: str  # Formato HH:MM
    total_price: Optional[Decimal] = None
    client_name: Optional[str] = None
    services: str  # String formatada com nomes dos serviços (ex: "Corte, Barba")


class UpcomingAppointmentDay(BaseModel):
    """Agrupamento de agendamentos por dia."""
    date: str  # Formato YYYY-MM-DD
    date_label: str  # Label formatado (ex: "Hoje", "Amanhã", "15 de Janeiro")
    appointments: List[UpcomingAppointmentItem]


class UpcomingAppointmentsResponse(BaseModel):
    """Resposta do endpoint de próximos agendamentos."""
    days: List[UpcomingAppointmentDay]


@router.get(
    "/upcoming",
    response_model=UpcomingAppointmentsResponse,
    summary="Obter próximos agendamentos",
    description="Retorna agendamentos futuros agrupados por dia, ordenados por horário. Usa notification_days do tenant para determinar o período."
)
async def get_upcoming_appointments(
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna agendamentos futuros agrupados por dia.
    
    Busca agendamentos onde start_datetime > agora e <= hoje + notification_days.
    Ordena por start_datetime ASC (mais próximos primeiro).
    Agrupa por dia na resposta.
    
    Args:
        tenant: Tenant autenticado (contém notification_days)
        db: Sessão do banco de dados
        
    Returns:
        UpcomingAppointmentsResponse: Agendamentos agrupados por dia
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(status_code=400, detail="tenant_id inválido")
        
        # Obter notification_days do tenant (padrão: 3)
        notification_days = getattr(tenant, 'notification_days', None) or 3
        
        # Calcular período: agora até hoje + N dias
        # IMPORTANTE: Usar timezone do Brasil (America/Sao_Paulo) para calcular "hoje"
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            # Fallback para Python < 3.9
            from backports.zoneinfo import ZoneInfo
        
        brazil_tz = ZoneInfo('America/Sao_Paulo')
        
        # Obter data/hora atual no timezone do Brasil
        now_brazil = datetime.now(brazil_tz)
        
        # Obter apenas a data (sem horário) no timezone do Brasil
        today_brazil = now_brazil.date()
        
        # Calcular data final (hoje + N dias) no timezone do Brasil
        end_date_brazil = today_brazil + timedelta(days=notification_days)
        
        # Converter para UTC para consultar no banco de dados
        # Agora no Brasil em UTC (timezone-naive)
        now_utc = now_brazil.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
        
        # Data final no Brasil convertida para UTC
        # Fim do dia (23:59:59.999999) no timezone do Brasil
        end_datetime_brazil = datetime.combine(end_date_brazil, datetime.max.time().replace(microsecond=999999))
        end_datetime_brazil = end_datetime_brazil.replace(tzinfo=brazil_tz)
        end_datetime = end_datetime_brazil.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
        
        # Buscar agendamentos futuros (não cancelados, não bloqueios manuais)
        # JOIN com Client para pegar client_name
        # JOIN com AppointmentService e Service para pegar nomes dos serviços
        appointments_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.start_datetime > now_utc,
                Appointment.start_datetime <= end_datetime,
                Appointment.status != AppointmentStatus.CANCELED,
                Appointment.is_manual_block == False
            )
        ).options(
            selectinload(Appointment.client),  # Carregar cliente relacionado
            selectinload(Appointment.services)  # Carregar serviços relacionados
        ).order_by(
            Appointment.start_datetime.asc()  # Ordenar por horário (mais próximo primeiro)
        )
        
        appointments_result = await db.execute(appointments_query)
        appointments = appointments_result.scalars().all()
        
        # Agrupar por dia
        from collections import defaultdict
        
        # Função para formatar label do dia
        def format_date_label(appointment_date: date) -> str:
            # Usar a data de hoje no Brasil que já foi calculada
            if appointment_date == today_brazil:
                return "Hoje"
            elif appointment_date == today_brazil + timedelta(days=1):
                return "Amanhã"
            else:
                # Formato: "15 de Janeiro"
                months_pt = [
                    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
                ]
                return f"{appointment_date.day} de {months_pt[appointment_date.month - 1]}"
        
        # Agrupar agendamentos por dia
        appointments_by_day = defaultdict(list)
        
        for apt in appointments:
            # Extrair data (sem hora) do start_datetime
            # IMPORTANTE: Converter para timezone do Brasil antes de extrair a data
            # O start_datetime está em UTC no banco (timezone-naive), então precisamos converter
            apt_datetime_utc = apt.start_datetime
            
            # Garantir que o datetime seja tratado como UTC (timezone-naive)
            # Se já tiver timezone, remover e tratar como UTC
            if apt_datetime_utc.tzinfo is not None:
                # Se já tiver timezone, converter para UTC primeiro (removendo timezone)
                apt_datetime_utc = apt_datetime_utc.replace(tzinfo=None)
            
            # Agora garantir que seja tratado como UTC (timezone-aware)
            apt_datetime_utc_aware = apt_datetime_utc.replace(tzinfo=ZoneInfo('UTC'))
            
            # Converter para timezone do Brasil
            apt_datetime_brazil = apt_datetime_utc_aware.astimezone(brazil_tz)
            
            # Extrair apenas a data no timezone do Brasil
            apt_date = apt_datetime_brazil.date()
            date_str = apt_date.isoformat()  # YYYY-MM-DD
            
            # Formatar horário no timezone do Brasil também
            start_time_str = apt_datetime_brazil.strftime("%H:%M")
            
            # Obter nome do cliente (prioridade: client.name > customer_name)
            client_name = None
            if apt.client:
                client_name = apt.client.name
            elif apt.customer_name:
                client_name = apt.customer_name
            
            # Obter nomes dos serviços
            service_names = []
            if apt.services:
                service_names = [s.name for s in apt.services]
            
            # Formatar string de serviços (ex: "Corte, Barba" ou "Combo")
            services_str = ", ".join(service_names) if service_names else "Sem serviço"
            
            # Criar item de agendamento
            appointment_item = UpcomingAppointmentItem(
                id=str(apt.id),
                start_time=start_time_str,
                total_price=Decimal(str(apt.total_value)) if apt.total_value else None,
                client_name=client_name,
                services=services_str
            )
            
            appointments_by_day[date_str].append(appointment_item)
        
        # Converter para lista de UpcomingAppointmentDay
        days_list = []
        for date_str in sorted(appointments_by_day.keys()):  # Ordenar por data
            apt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            date_label = format_date_label(apt_date)
            
            # Ordenar agendamentos do dia por horário (já vem ordenado, mas garantir)
            appointments_for_day = sorted(
                appointments_by_day[date_str],
                key=lambda x: x.start_time
            )
            
            day_group = UpcomingAppointmentDay(
                date=date_str,
                date_label=date_label,
                appointments=appointments_for_day
            )
            days_list.append(day_group)
        
        return UpcomingAppointmentsResponse(days=days_list)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar próximos agendamentos: {str(e)}"
        )

