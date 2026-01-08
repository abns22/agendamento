"""
Endpoints administrativos para gerenciamento de Agendamentos.

Permite que administradores visualizem e gerenciem agendamentos de clientes.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query, BackgroundTasks, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
import uuid
import asyncio

from app.core.database import get_db
from app.core.dependencies import verify_subscription_access
from app.models.tenant import Tenant
from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_service import AppointmentService as AppointmentServiceModel
from app.models.service import Service
from app.models.client import Client
from app.models.payment_entry import PaymentEntry
from app.models.schedule_config import ScheduleConfig
import logging

logger = logging.getLogger(__name__)

from app.schemas.appointment import (
    AppointmentResponse,
    AppointmentCancelRequest,
    ManualAppointmentCreate,
    AppointmentRescheduleRequest,
    AppointmentUpdate
)
from app.schemas.transaction import FinalizeAppointmentRequest, FinalizeAppointmentResponse, TransactionResponse
from app.services.finalization_service import FinalizationService
from app.services.whatsapp_service import WhatsAppService
from app.services.availability_service import AvailabilityService
from app.services.appointment_service import AppointmentService
from app.services.promotion_service import PromotionService
from pydantic import BaseModel
from datetime import timedelta

router = APIRouter(prefix="/admin/appointments", tags=["Admin - Appointments"])


async def build_appointment_response(
    appointment: Appointment,
    db: AsyncSession
) -> AppointmentResponse:
    """
    Constrói AppointmentResponse com informações dos serviços relacionados.
    
    Args:
        appointment: Objeto Appointment
        db: Sessão do banco de dados
        
    Returns:
        AppointmentResponse: Response com informações dos serviços
    """
    # IMPORTANTE: Não fazer refresh se a sessão já foi commitada
    # O refresh pode causar problemas se a sessão não estiver mais ativa
    # Os serviços já devem estar carregados via selectinload
    try:
        # Tentar refresh apenas se a sessão ainda estiver ativa
        if appointment.services is None or len(appointment.services) == 0:
            await db.refresh(appointment, ['services'])
    except Exception as refresh_error:
        # Se o refresh falhar, tentar carregar os serviços manualmente
        logger.warning(f"⚠️ Erro ao fazer refresh, carregando serviços manualmente: {str(refresh_error)}")
        pass
    
    apt_dict = AppointmentResponse.model_validate(appointment).model_dump()
    
    # Se houver serviços na relação Many-to-Many
    if appointment.services:
        services = list(appointment.services)
        apt_dict['service_ids'] = [str(s.id) for s in services]
        apt_dict['service_names'] = [s.name for s in services]
        apt_dict['service_display_color_codes'] = [s.display_color_code for s in services if s.display_color_code]
        
        # Para compatibilidade, usar primeiro serviço
        first_service = services[0]
        apt_dict['service_name'] = first_service.name
        apt_dict['service_display_color_code'] = first_service.display_color_code
        apt_dict['service_id'] = first_service.id
    # Se não houver serviços na relação mas tiver service_id (dados antigos)
    elif appointment.service_id:
        service_id_str = str(appointment.service_id)
        service_query = select(Service).where(Service.id == service_id_str)
        service_result = await db.execute(service_query)
        service = service_result.scalar_one_or_none()
        if service:
            apt_dict['service_id'] = service.id
            apt_dict['service_name'] = service.name
            apt_dict['service_display_color_code'] = service.display_color_code
            apt_dict['service_ids'] = [str(service.id)]
            apt_dict['service_names'] = [service.name]
            apt_dict['service_display_color_codes'] = [service.display_color_code] if service.display_color_code else []
        else:
            apt_dict['service_name'] = None
            apt_dict['service_display_color_code'] = None
            apt_dict['service_ids'] = []
            apt_dict['service_names'] = []
            apt_dict['service_display_color_codes'] = []
    else:
        # Bloqueio manual sem serviços
        apt_dict['service_name'] = None
        apt_dict['service_display_color_code'] = None
        apt_dict['service_ids'] = []
        apt_dict['service_names'] = []
        apt_dict['service_display_color_codes'] = []
    
    # Adicionar total_value se disponível
    if appointment.total_value:
        apt_dict['total_value'] = float(appointment.total_value)
    
    return AppointmentResponse(**apt_dict)


@router.get(
    "/availability",
    response_model=dict,
    summary="Buscar disponibilidade geral",
    description="Retorna todos os horários disponíveis para uma data específica, usando a menor duração de serviço disponível."
)
async def get_availability(
    date: str = Query(..., description="Data no formato YYYY-MM-DD"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Busca horários disponíveis para uma data específica.
    
    Para agendamento manual, retorna todos os slots disponíveis usando
    a menor duração de serviço disponível no tenant.
    
    Args:
        date: Data no formato YYYY-MM-DD
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        dict: Objeto com date e lista de available_slots
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(status_code=400, detail="tenant_id inválido")
        
        # Validar formato de data
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Data deve estar no formato YYYY-MM-DD")
        
        # Buscar o primeiro serviço do tenant para usar sua duração
        # (ou o serviço com menor duração)
        services_query = select(Service).where(
            Service.tenant_id == tenant_id_str
        ).order_by(Service.duration_minutes.asc())
        
        services_result = await db.execute(services_query)
        services = services_result.scalars().all()
        
        if not services:
            # Se não houver serviços, retornar lista vazia
            return {
                'date': date,
                'available_slots': []
            }
        
        # Usar o primeiro serviço (menor duração) para calcular disponibilidade
        first_service = services[0]
        
        # Usar AvailabilityService para calcular slots
        from uuid import UUID
        available_slots = await AvailabilityService.get_available_slots(
            db_session=db,
            tenant_id=UUID(tenant_id_str),
            service_id=UUID(str(first_service.id)),
            date_str=date
        )
        
        return {
            'date': date,
            'available_slots': available_slots
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar disponibilidade: {str(e)}"
        )


@router.get(
    "/count",
    response_model=dict,
    summary="Contar agendamentos futuros",
    description="Retorna a contagem de agendamentos não cancelados do tenant para os próximos N dias (a partir de amanhã)."
)
async def count_future_appointments(
    days: Optional[int] = Query(
        default=None,
        description="Número de dias para buscar (opcional, usa notification_days do tenant se não fornecido)"
    ),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Conta agendamentos futuros não cancelados do tenant.
    
    Busca agendamentos que:
    - Não estão cancelados (status != 'CANCELED')
    - Começam a partir de amanhã (dia seguinte ao atual)
    - Até N dias no futuro (onde N é o parâmetro days ou notification_days do tenant)
    
    Args:
        days: Número de dias para buscar (opcional, padrão: notification_days do tenant ou 3)
        tenant: Tenant autenticado (injetado via get_current_active_tenant)
        db: Sessão do banco de dados
        
    Returns:
        dict: {"count": int, "days": int} - Contagem e número de dias usado
        
    Raises:
        HTTPException 500: Erro interno do servidor
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(status_code=400, detail="tenant_id inválido")
        
        # Determinar número de dias (parâmetro ou valor do tenant ou padrão 3)
        days_to_use = days
        if days_to_use is None:
            # Usar notification_days do tenant se disponível, senão padrão 3
            days_to_use = getattr(tenant, 'notification_days', None) or 3

        # Garantir que days_to_use esteja dentro de um intervalo seguro (1 a 30)
        try:
            days_to_use_int = int(days_to_use)
        except (TypeError, ValueError):
            days_to_use_int = 3

        if days_to_use_int < 1:
            days_to_use_int = 1
        if days_to_use_int > 30:
            days_to_use_int = 30

        days_to_use = days_to_use_int
        
        # Calcular período: de amanhã até N dias no futuro
        today = date.today()
        tomorrow = today + timedelta(days=1)
        end_date = today + timedelta(days=days_to_use)
        
        # Converter para datetime (início e fim do período)
        start_datetime = datetime.combine(tomorrow, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Buscar agendamentos não cancelados no período
        count_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.start_datetime >= start_datetime,
                Appointment.start_datetime <= end_datetime,
                Appointment.status != AppointmentStatus.CANCELED
            )
        )
        
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0
        
        return {
            "count": count,
            "days": days_to_use
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao contar agendamentos futuros: {str(e)}"
        )


class AppointmentUpdate(BaseModel):
    """Schema para atualização de agendamento."""
    status: Optional[str] = None


@router.get(
    "",
    response_model=List[AppointmentResponse],
    summary="Listar agendamentos",
    description="Retorna todos os agendamentos do tenant autenticado com filtros avançados. Sempre ordenado por start_datetime ASC."
)
async def list_appointments(
    search: Optional[str] = Query(None, description="Busca por texto (nome do cliente ou e-mail). Busca parcial e insensível a maiúsculas."),
    service_id: Optional[UUID] = Query(None, description="Filtrar agendamentos que contenham um serviço específico."),
    start_date: Optional[str] = Query(None, description="Data inicial do período (YYYY-MM-DD). Ignorado se days_ahead for fornecido."),
    end_date: Optional[str] = Query(None, description="Data final do período (YYYY-MM-DD). Ignorado se days_ahead for fornecido."),
    days_ahead: Optional[int] = Query(None, ge=1, description="Número de dias a partir de hoje (1, 2, 7, 30). Sobrescreve start_date/end_date."),
    status: Optional[str] = Query(None, description="Status para filtrar (SCHEDULED, CONFIRMED, COMPLETED, CANCELED)."),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os agendamentos do tenant autenticado com filtros avançados.
    
    Filtros disponíveis:
    - search: Busca por nome do cliente ou e-mail (busca parcial, case-insensitive)
    - service_id: Filtra agendamentos que contenham um serviço específico
    - start_date/end_date: Filtra por período (YYYY-MM-DD)
    - days_ahead: Calcula período automaticamente (hoje até hoje + X dias). Sobrescreve start_date/end_date
    - status: Filtra por status do agendamento
    
    Ordenação: Sempre ordenado por start_datetime ASC (mais próximos primeiro).
    
    Performance: Usa JOIN eficiente para evitar N+1 queries.
    
    Args:
        search: Termo de busca por nome do cliente ou e-mail
        service_id: ID do serviço para filtrar
        start_date: Data inicial do período (YYYY-MM-DD)
        end_date: Data final do período (YYYY-MM-DD)
        days_ahead: Número de dias a partir de hoje (sobrescreve start_date/end_date)
        status: Status do agendamento para filtrar
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[AppointmentResponse]: Lista de agendamentos ordenados por horário
    """
    # Construir query base com JOIN otimizado para evitar N+1
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(
            status_code=400,
            detail="tenant_id inválido"
        )
    
    # Query base com selectinload para carregar serviços de forma eficiente
    query = select(Appointment).options(
        selectinload(Appointment.services)
    ).where(
        Appointment.tenant_id == tenant_id_str
    )
    
    # LÓGICA DE PRIORIDADE: days_ahead sobrescreve start_date/end_date
    if days_ahead:
        # Calcular período automaticamente: hoje até hoje + X dias
        # IMPORTANTE: Usar timezone do Brasil (America/Sao_Paulo) para calcular "hoje"
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            # Fallback para Python < 3.9
            from backports.zoneinfo import ZoneInfo
        
        brazil_tz = ZoneInfo('America/Sao_Paulo')
        
        # Obter a data/hora atual no timezone do Brasil
        now_brazil = datetime.now(brazil_tz)
        
        # Obter apenas a data (sem horário) no timezone do Brasil
        today_brazil = now_brazil.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Converter para UTC para consultar no banco de dados
        # O datetime no timezone do Brasil é timezone-aware, então convertemos para UTC
        start_dt = today_brazil.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
        
        # Calcular data final (hoje + days_ahead) no timezone do Brasil
        end_date_brazil = today_brazil + timedelta(days=days_ahead)
        end_date_brazil = end_date_brazil.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Converter para UTC
        end_dt = end_date_brazil.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
        
        query = query.where(
            and_(
                Appointment.start_datetime >= start_dt,
                Appointment.start_datetime <= end_dt
            )
        )
    else:
        # Usar start_date/end_date se days_ahead não foi fornecido
        if start_date or end_date:
            conditions = []
            
            if start_date:
                try:
                    # Parse da data (YYYY-MM-DD)
                    # Quando o usuário seleciona dia 12, queremos agendamentos que acontecem no dia 12 no Brasil
                    # 
                    # Exemplo: Dia 12/01 no Brasil
                    # - 00:00:00 BRT do dia 12 = 03:00:00 UTC do dia 12
                    # - 23:59:59 BRT do dia 12 = 02:59:59 UTC do dia 13
                    # 
                    # Para capturar todos os agendamentos do dia 12 no Brasil:
                    # - start_datetime >= 03:00:00 UTC do dia 12 (início do dia 12 no Brasil)
                    # - start_datetime < 03:00:00 UTC do dia 13 (início do dia 13 no Brasil)
                    
                    parsed_date = datetime.strptime(start_date, '%Y-%m-%d')
                    
                    # Criar datetime UTC para início do dia no Brasil
                    # 00:00:00 BRT = 03:00:00 UTC (considerando UTC-3)
                    start_dt_utc = datetime(
                        parsed_date.year, parsed_date.month, parsed_date.day,
                        hour=3, minute=0, second=0, microsecond=0
                    )
                    
                    conditions.append(Appointment.start_datetime >= start_dt_utc)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date deve estar no formato YYYY-MM-DD"
                    )
            
            if end_date:
                try:
                    # Parse da data (YYYY-MM-DD)
                    parsed_date = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    # Criar datetime UTC para início do dia seguinte no Brasil
                    # Isso garante que capturamos até 23:59:59 BRT do dia selecionado
                    # 00:00:00 BRT do dia seguinte = 03:00:00 UTC do dia seguinte
                    end_dt_utc = datetime(
                        parsed_date.year, parsed_date.month, parsed_date.day,
                        hour=3, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)  # Próximo dia às 03:00:00 UTC
                    
                    # Usar < para não incluir o início do próximo dia
                    conditions.append(Appointment.start_datetime < end_dt_utc)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="end_date deve estar no formato YYYY-MM-DD"
                    )
            
            if conditions:
                query = query.where(and_(*conditions))
    
    # Aplicar filtro de busca por texto (nome do cliente ou e-mail)
    if search:
        search_term = f"%{search.lower()}%"
        # Buscar em customer_name (campo do appointment) ou no nome do cliente relacionado
        # Usar LEFT JOIN com Client para buscar também no nome do cliente
        from sqlalchemy.orm import aliased
        client_alias = aliased(Client)
        
        # Adicionar JOIN com Client (LEFT JOIN para não excluir agendamentos sem client_id)
        query = query.outerjoin(
            client_alias,
            and_(
                Appointment.client_id == client_alias.id,
                client_alias.tenant_id == tenant_id_str
            )
        )
        
        # Buscar em customer_name (campo do appointment) OU no nome/email do cliente relacionado
        search_conditions = [
            func.lower(Appointment.customer_name).like(search_term),
            func.lower(client_alias.name).like(search_term),
            func.lower(client_alias.email).like(search_term)
        ]
        
        query = query.where(or_(*search_conditions))
    
    # Aplicar filtro de service_id usando JOIN com AppointmentService
    if service_id:
        service_id_str = str(service_id)
        # JOIN com AppointmentService para buscar agendamentos que contenham o serviço
        query = query.join(
            AppointmentServiceModel,
            AppointmentServiceModel.appointment_id == Appointment.id
        ).where(
            AppointmentServiceModel.service_id == service_id_str
        )
    
    # Aplicar filtro de status se fornecido
    if status:
        try:
            status_enum = AppointmentStatus(status.upper())
            query = query.where(Appointment.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido. Use: SCHEDULED, CONFIRMED, COMPLETED, CANCELED"
            )
    
    # Ordenar por horário de início (ORDENAÇÃO OBRIGATÓRIA - ASC)
    query = query.order_by(Appointment.start_datetime.asc())
    
    # Executar query
    # Se houver JOINs (search ou service_id), usar distinct() para evitar duplicatas
    if search or service_id:
        query = query.distinct()
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    # Construir responses com informações dos serviços
    # Como já carregamos os serviços com selectinload, não precisamos fazer queries adicionais
    appointment_responses = []
    for apt in appointments:
        response = await build_appointment_response(apt, db)
        appointment_responses.append(response)
    
    return appointment_responses


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Obter agendamento",
    description="Retorna um agendamento específico do tenant autenticado."
)
async def get_appointment(
    appointment_id: UUID = Path(..., description="UUID do agendamento"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtém um agendamento específico.
    
    Args:
        appointment_id: UUID do agendamento
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        AppointmentResponse: Dados do agendamento
        
    Raises:
        HTTPException 404: Se o agendamento não for encontrado ou não pertencer ao tenant
    """
    # IMPORTANTE: Converter tenant_id e appointment_id para strings (MySQL armazena UUIDs como String(36))
    tenant_id_str = str(tenant.id) if tenant.id else None
    appointment_id_str = str(appointment_id) if appointment_id else None
    
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.id == appointment_id_str,
                Appointment.tenant_id == tenant_id_str
            )
        )
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Agendamento não encontrado"
        )
    
    return await build_appointment_response(appointment, db)


@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Atualizar agendamento",
    description="Atualiza um agendamento existente (status, horário, serviços). Valida conflitos de horário ao editar."
)
async def update_appointment(
    request: Request,
    appointment_id: UUID = Path(..., description="UUID do agendamento"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza um agendamento existente.
    
    Permite atualizar:
    - Status do agendamento
    - Horário de início (start_datetime)
    - Lista de serviços (service_ids)
    
    Ao editar horário ou serviços, valida conflitos de disponibilidade:
    - Calcula a soma das durações dos serviços
    - Calcula novo horário de fim (start_time + soma_duracoes)
    - Verifica conflitos com outros agendamentos (excluindo o próprio)
    - Retorna 409 Conflict se houver conflito
    
    Args:
        appointment_id: UUID do agendamento
        update_data: Dados para atualização (AppointmentUpdate)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        AppointmentResponse: Agendamento atualizado
        
    Raises:
        HTTPException 404: Se o agendamento não for encontrado
        HTTPException 400: Se os dados forem inválidos
        HTTPException 409: Se houver conflito de horário
    """
    # IMPORTANTE: Converter tenant_id e appointment_id para strings (MySQL armazena UUIDs como String(36))
    tenant_id_str = str(tenant.id) if tenant.id else None
    appointment_id_str = str(appointment_id) if appointment_id else None
    
    # IMPORTANTE: Fazer parse manual do JSON porque o Pydantic não está recebendo os campos
    # Ler o body diretamente do request
    try:
        raw_body = await request.json()
        print(f"📦 RAW BODY do request: {raw_body}")
        
        # Criar AppointmentUpdate a partir do raw_body
        update_data = AppointmentUpdate(**raw_body)
        print(f"✅ AppointmentUpdate criado a partir do raw_body: {update_data.model_dump(exclude_none=False)}")
    except Exception as e:
        print(f"❌ Erro ao fazer parse do body: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar dados da requisição: {str(e)}"
        )
    
    # DEBUG: Log do que foi recebido no update_data
    # IMPORTANTE: Usar model_dump(exclude_none=False) para ver TODOS os campos, incluindo None
    update_data_dict = update_data.model_dump(exclude_none=False) if hasattr(update_data, 'model_dump') else 'N/A'
    start_datetime_raw = getattr(update_data, 'start_datetime', 'NOT_FOUND')
    service_ids_raw = getattr(update_data, 'service_ids', 'NOT_FOUND')
    
    print(f"📥 RECEBENDO UPDATE REQUEST | ID: {appointment_id_str} | update_data (exclude_none=False): {update_data_dict} | start_datetime: {start_datetime_raw} | service_ids: {service_ids_raw}")
    logger.info(
        f"📥 RECEBENDO UPDATE REQUEST | "
        f"ID: {appointment_id_str} | "
        f"update_data type: {type(update_data)} | "
        f"update_data dict: {update_data_dict} | "
        f"start_datetime raw: {start_datetime_raw} | "
        f"start_datetime type: {type(getattr(update_data, 'start_datetime', None))} | "
        f"service_ids raw: {service_ids_raw}"
    )
    
    # Buscar agendamento existente
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.id == appointment_id_str,
                Appointment.tenant_id == tenant_id_str
            )
        )
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Agendamento não encontrado"
        )
    
    # Não permitir editar agendamentos cancelados ou finalizados
    if appointment.status == AppointmentStatus.CANCELED:
        raise HTTPException(
            status_code=400,
            detail="Não é possível editar um agendamento cancelado"
        )
    
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Não é possível editar um agendamento finalizado"
        )
    
    # IMPORTANTE: Obter dados via model_dump() primeiro, que é mais confiável
    # O Pydantic pode ter validado e convertido os dados, então model_dump() mostra o estado final
    data_dict = update_data.model_dump()
    print(f"📋 model_dump completo: {data_dict}")
    
    # Determinar quais serviços usar (novos ou atuais)
    has_service_ids = False
    service_ids_provided = None
    
    # Verificar service_ids no dict
    if 'service_ids' in data_dict and data_dict['service_ids'] is not None:
        service_ids_list = data_dict['service_ids']
        if isinstance(service_ids_list, list) and len(service_ids_list) > 0:
            has_service_ids = True
            # Converter strings para UUIDs se necessário
            try:
                service_ids_provided = [UUID(str(sid)) if not isinstance(sid, UUID) else sid for sid in service_ids_list]
                print(f"✅ service_ids detectado: {service_ids_provided}")
            except (ValueError, TypeError) as e:
                print(f"❌ Erro ao converter service_ids para UUIDs: {str(e)}")
                has_service_ids = False
    
    # Determinar service_ids_to_use: usar os fornecidos ou buscar os atuais
    if has_service_ids and service_ids_provided:
        service_ids_to_use = service_ids_provided
    else:
        # Buscar serviços atuais do agendamento
        await db.refresh(appointment, ['services'])
        if appointment.services:
            service_ids_to_use = [UUID(str(s.id)) for s in appointment.services]
        elif appointment.service_id:
            service_ids_to_use = [UUID(str(appointment.service_id))]
        else:
            raise HTTPException(
                status_code=400,
                detail="Agendamento não possui serviços associados e nenhum service_ids foi fornecido"
            )
    
    # Determinar qual horário usar (novo ou atual)
    # IMPORTANTE: Usar model_dump() que já foi obtido acima
    update_start_datetime = None
    
    if 'start_datetime' in data_dict and data_dict['start_datetime'] is not None:
        start_dt_value = data_dict['start_datetime']
        print(f"🔍 start_datetime no dict: {start_dt_value} | type: {type(start_dt_value)}")
        
        # Se já é datetime, usar diretamente
        if isinstance(start_dt_value, datetime):
            update_start_datetime = start_dt_value
            print(f"✅ start_datetime já é datetime: {update_start_datetime}")
        # Se é string, fazer parse
        elif isinstance(start_dt_value, str):
            try:
                # IMPORTANTE: O datetime vem do frontend em UTC (ISO string)
                # Precisamos converter para o horário local do Brasil antes de salvar
                # O MySQL armazena no horário local do servidor (Brasil)
                
                # Fazer parse do datetime ISO (pode ter timezone ou não)
                if start_dt_value.endswith('Z'):
                    # Formato UTC: 2026-01-17T11:00:00.000Z
                    date_str = start_dt_value.replace('Z', '+00:00')
                    parsed_dt = datetime.fromisoformat(date_str)
                elif '+' in start_dt_value or start_dt_value.count('-') > 2:
                    # Formato com timezone: 2026-01-17T11:00:00+00:00
                    parsed_dt = datetime.fromisoformat(start_dt_value)
                else:
                    # Formato sem timezone: 2026-01-17T11:00:00 (assumir UTC)
                    parsed_dt = datetime.fromisoformat(start_dt_value)
                    # Assumir que está em UTC se não tiver timezone
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                
                # Se o datetime tem timezone, converter para o horário local do Brasil
                if parsed_dt.tzinfo is not None:
                    # Importar ZoneInfo para timezone do Brasil
                    try:
                        from zoneinfo import ZoneInfo
                    except ImportError:
                        from backports.zoneinfo import ZoneInfo
                    
                    brazil_tz = ZoneInfo('America/Sao_Paulo')
                    # Converter de UTC para horário do Brasil
                    dt_brazil = parsed_dt.astimezone(brazil_tz)
                    # Remover timezone para salvar no MySQL (que está no horário local)
                    update_start_datetime = dt_brazil.replace(tzinfo=None)
                    print(f"✅ start_datetime convertido de UTC para Brasil: {parsed_dt} -> {update_start_datetime}")
                else:
                    # Se não tem timezone, assumir que já está no horário local do Brasil
                    update_start_datetime = parsed_dt
                    print(f"✅ start_datetime parseado (sem timezone, assumindo Brasil): {update_start_datetime}")
            except Exception as parse_error:
                print(f"❌ Erro ao fazer parse de start_datetime '{start_dt_value}': {str(parse_error)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato de data/hora inválido: {str(parse_error)}"
                )
        else:
            print(f"⚠️ start_datetime tem tipo inesperado: {type(start_dt_value)}")
    else:
        print(f"⚠️ start_datetime não encontrado no dict ou é None")
    
    # DEBUG: Verificar o que foi recebido
    print(f"🔍 VERIFICANDO start_datetime | ID: {appointment_id_str} | type: {type(update_start_datetime)} | value: {update_start_datetime} | is None: {update_start_datetime is None}")
    logger.info(
        f"🔍 VERIFICANDO start_datetime | "
        f"ID: {appointment_id_str} | "
        f"update_start_datetime type: {type(update_start_datetime)} | "
        f"update_start_datetime value: {update_start_datetime} | "
        f"is None: {update_start_datetime is None} | "
        f"hasattr check: {hasattr(update_data, 'start_datetime')}"
    )
    
    has_start_datetime = update_start_datetime is not None
    new_start_datetime = update_start_datetime if has_start_datetime else appointment.start_datetime
    
    # Garantir que o datetime está timezone-naive (já convertido para horário local do Brasil)
    if new_start_datetime and hasattr(new_start_datetime, 'tzinfo') and new_start_datetime.tzinfo is not None:
        # Se ainda tem timezone, converter para horário local do Brasil
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo
        
        brazil_tz = ZoneInfo('America/Sao_Paulo')
        dt_brazil = new_start_datetime.astimezone(brazil_tz)
        new_start_datetime = dt_brazil.replace(tzinfo=None)
        print(f"🔄 Convertendo datetime com timezone para Brasil: {new_start_datetime}")
    
    # DEBUG: Log para verificar o que está sendo recebido
    print(f"🔄 UPDATE APPOINTMENT DEBUG | ID: {appointment_id_str} | has_start_datetime: {has_start_datetime} | has_service_ids: {has_service_ids} | will_update: {has_start_datetime or has_service_ids}")
    logger.info(
        f"🔄 UPDATE APPOINTMENT DEBUG | "
        f"ID: {appointment_id_str} | "
        f"has_start_datetime: {has_start_datetime} | "
        f"update_start_datetime: {update_start_datetime} | "
        f"new_start_datetime: {new_start_datetime} | "
        f"has_service_ids: {has_service_ids} | "
        f"service_ids_provided: {service_ids_provided} | "
        f"service_ids_to_use: {service_ids_to_use} | "
        f"original_start: {appointment.start_datetime} | "
        f"original_services_count: {len(appointment.services) if appointment.services else 0}"
    )
    
    # DEBUG: Verificar se vai entrar no bloco de atualização
    will_update = has_start_datetime or has_service_ids
    print(f"🔍 VERIFICANDO ATUALIZAÇÃO | ID: {appointment_id_str} | has_start_datetime: {has_start_datetime} | has_service_ids: {has_service_ids} | will_update: {will_update}")
    logger.info(
        f"🔍 VERIFICANDO ATUALIZAÇÃO | "
        f"ID: {appointment_id_str} | "
        f"has_start_datetime: {has_start_datetime} | "
        f"has_service_ids: {has_service_ids} | "
        f"will_update: {will_update}"
    )
    
    if has_start_datetime or has_service_ids:
        print(f"✅ ENTRANDO NO BLOCO DE ATUALIZAÇÃO | ID: {appointment_id_str}")
        logger.info(f"✅ ENTRANDO NO BLOCO DE ATUALIZAÇÃO | ID: {appointment_id_str}")
        # 1. Calcular soma das durações dos serviços
        total_duration_minutes = 0
        services_to_use = []
        total_value = Decimal('0.00')
        
        for service_id in service_ids_to_use:
            service_id_str = str(service_id)
            service_query = select(Service).where(
                and_(
                    Service.id == service_id_str,
                    Service.tenant_id == tenant_id_str
                )
            )
            service_result = await db.execute(service_query)
            service = service_result.scalar_one_or_none()
            
            if not service:
                raise HTTPException(
                    status_code=404,
                    detail=f"Serviço não encontrado: {service_id}"
                )
            
            services_to_use.append(service)
            total_duration_minutes += service.duration_minutes
            
            # Calcular valor total (com promoções)
            effective_price = Decimal(str(PromotionService.get_effective_price(service)))
            total_value += effective_price
        
        # 2. Calcular novo horário de fim
        new_end_datetime = new_start_datetime + timedelta(minutes=total_duration_minutes)
        
        # 3. Buscar conflitos (excluindo o próprio agendamento)
        # Regra de Ouro: (start_time < novo_fim) AND (end_time > start_time)
        conflicting_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.id != appointment_id_str,  # Excluir o próprio agendamento
                Appointment.start_datetime < new_end_datetime,
                Appointment.end_datetime > new_start_datetime,
                Appointment.status != AppointmentStatus.CANCELED  # Ignorar cancelados
            )
        )
        conflicting_result = await db.execute(conflicting_query)
        conflicting_appointments = conflicting_result.scalars().all()
        
        # 4. Se houver conflito, retornar 409 Conflict
        if conflicting_appointments:
            raise HTTPException(
                status_code=409,
                detail="O tempo total dos serviços selecionados ultrapassa o horário disponível até o próximo agendamento."
            )
        
        # 5. Se não houver conflito, atualizar dados
        # IMPORTANTE: Atualizar os campos diretamente no objeto
        appointment.start_datetime = new_start_datetime
        appointment.end_datetime = new_end_datetime
        appointment.total_value = total_value
        
        # DEBUG: Log para verificar o que está sendo atualizado
        logger.info(
            f"💾 UPDATING APPOINTMENT | "
            f"ID: {appointment_id_str} | "
            f"start_datetime: {appointment.start_datetime} | "
            f"end_datetime: {appointment.end_datetime} | "
            f"total_value: {appointment.total_value} | "
            f"services_count: {len(services_to_use)}"
        )
        
        # Atualizar relacionamento com serviços
        # Primeiro, buscar e remover todos os AppointmentService antigos
        old_appointment_services_query = select(AppointmentServiceModel).where(
            AppointmentServiceModel.appointment_id == appointment_id_str
        )
        old_appointment_services_result = await db.execute(old_appointment_services_query)
        old_appointment_services = old_appointment_services_result.scalars().all()
        
        for old_appointment_service in old_appointment_services:
            await db.delete(old_appointment_service)
        
        # IMPORTANTE: Fazer flush antes de adicionar novos serviços para garantir que as deleções sejam processadas
        await db.flush()
        
        # Adicionar novos serviços
        for service in services_to_use:
            new_appointment_service = AppointmentServiceModel(
                appointment_id=appointment_id_str,
                service_id=str(service.id)
            )
            db.add(new_appointment_service)
        
        # Atualizar service_id para compatibilidade (primeiro serviço)
        if services_to_use:
            appointment.service_id = str(services_to_use[0].id)
    
    # Atualizar status se fornecido
    if update_data.status:
        try:
            appointment.status = AppointmentStatus(update_data.status.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido. Use: PENDING, CONFIRMED, CANCELED, COMPLETED"
            )
    
    # IMPORTANTE: Fazer flush e commit para garantir que todas as mudanças sejam persistidas
    try:
        await db.flush()
        
        # DEBUG: Verificar estado antes do commit
        logger.info(
            f"💾 BEFORE COMMIT | "
            f"ID: {appointment_id_str} | "
            f"start_datetime: {appointment.start_datetime} | "
            f"end_datetime: {appointment.end_datetime} | "
            f"total_value: {appointment.total_value} | "
            f"service_id: {appointment.service_id}"
        )
        
        await db.commit()
        
        # DEBUG: Verificar estado após commit
        logger.info(
            f"✅ AFTER COMMIT | "
            f"ID: {appointment_id_str} | "
            f"start_datetime: {appointment.start_datetime} | "
            f"end_datetime: {appointment.end_datetime} | "
            f"commit successful: True"
        )
        
        # IMPORTANTE: Verificar se o commit foi realmente persistido
        # Fazendo uma query simples para garantir que a transação foi commitada
        test_query = select(func.count(Appointment.id)).where(
            Appointment.id == appointment_id_str
        )
        test_result = await db.execute(test_query)
        test_count = test_result.scalar()
        logger.info(
            f"🔍 VERIFICAÇÃO PÓS-COMMIT | "
            f"ID: {appointment_id_str} | "
            f"appointment_exists: {test_count > 0}"
        )
        
    except Exception as commit_error:
        await db.rollback()
        logger.error(
            f"❌ ERRO NO COMMIT | "
            f"ID: {appointment_id_str} | "
            f"Erro: {str(commit_error)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar alterações: {str(commit_error)}"
        )
    
    # IMPORTANTE: Após commit, fazer uma nova query para buscar o appointment atualizado
    # NÃO fazer expire_all() ou expire() após commit, pois pode causar rollback
    # A nova query já buscará os dados atualizados do banco
    
    # Aguardar um pequeno delay para garantir que o commit foi processado (especialmente em ambientes distribuídos)
    await asyncio.sleep(0.1)  # 100ms de delay
    
    appointment_query = select(Appointment).options(
        selectinload(Appointment.services),
        selectinload(Appointment.client)
    ).where(
        and_(
            Appointment.id == appointment_id_str,
            Appointment.tenant_id == tenant_id_str
        )
    )
    refreshed_result = await db.execute(appointment_query)
    refreshed_appointment = refreshed_result.scalar_one_or_none()
    
    if not refreshed_appointment:
        logger.error(f"❌ Agendamento não encontrado após atualização: {appointment_id_str}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao recarregar agendamento após atualização"
        )
    
    # DEBUG: Verificar dados retornados da query
    logger.info(
        f"📋 REFRESHED APPOINTMENT | "
        f"ID: {refreshed_appointment.id} | "
        f"start_datetime: {refreshed_appointment.start_datetime} | "
        f"end_datetime: {refreshed_appointment.end_datetime} | "
        f"services_count: {len(refreshed_appointment.services) if refreshed_appointment.services else 0} | "
        f"service_ids: {[str(s.id) for s in refreshed_appointment.services] if refreshed_appointment.services else []}"
    )
    
    return await build_appointment_response(refreshed_appointment, db)


@router.post(
    "/{appointment_id}/finalize",
    response_model=FinalizeAppointmentResponse,
    status_code=200,
    summary="Finalizar agendamento",
    description="Finaliza um agendamento, cria transação no caixa e registra formas de pagamento."
)
async def finalize_appointment(
    appointment_id: UUID = Path(..., description="UUID do agendamento"),
    finalize_data: FinalizeAppointmentRequest = ...,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Finaliza um agendamento e cria a transação no caixa.
    
    Esta rota:
    1. Valida o agendamento
    2. Calcula custos e aplica promoções
    3. Calcula taxas de pagamento
    4. Cria Transaction e PaymentEntry
    5. Atualiza Appointment para COMPLETED
    
    Args:
        appointment_id: UUID do agendamento
        finalize_data: Dados de finalização (formas de pagamento)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        FinalizeAppointmentResponse: Transação criada e agendamento atualizado
        
    Raises:
        HTTPException 404: Se o agendamento não for encontrado
        HTTPException 400: Se o agendamento já estiver finalizado ou dados inválidos
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Converter payment_entries para formato esperado pelo serviço
        payment_entries = [
            {
                'payment_method_id': str(pe.payment_method_id),
                'value_paid': float(pe.value_paid),
                'installments': pe.installments
            }
            for pe in finalize_data.payment_entries
        ]
        
        # Validar dados para pagamento futuro
        if not finalize_data.is_paid:
            if not finalize_data.client_name or not finalize_data.due_date:
                raise HTTPException(
                    status_code=400,
                    detail="client_name e due_date são obrigatórios quando is_paid=False"
                )
        
        # Chamar serviço de finalização
        transaction, appointment, debtor = await FinalizationService.finalize_appointment(
            db_session=db,
            tenant_id=tenant.id,
            appointment_id=appointment_id,
            payment_entries=payment_entries,
            additional_cost=finalize_data.additional_cost,
            discount=finalize_data.discount,
            is_paid=finalize_data.is_paid,
            client_name=finalize_data.client_name,
            client_phone=finalize_data.client_phone,
            due_date=finalize_data.due_date,
            value_due=finalize_data.value_due
        )
        
        # Buscar payment_entries para incluir na resposta
        payment_entries_query = select(PaymentEntry).where(
            PaymentEntry.transaction_id == str(transaction.id)
        )
        payment_entries_result = await db.execute(payment_entries_query)
        payment_entries_list = payment_entries_result.scalars().all()
        
        # Construir resposta manualmente para evitar erro de relacionamento assíncrono
        # Não usar model_validate diretamente no objeto Transaction pois tenta acessar payment_entries
        transaction_dict = {
            'id': UUID(str(transaction.id)),
            'tenant_id': UUID(str(transaction.tenant_id)),
            'appointment_id': UUID(str(transaction.appointment_id)),
            'date_time': transaction.date_time,
            'gross_value': transaction.gross_value,
            'net_value': transaction.net_value,
            'total_cost': transaction.total_cost,
            'total_profit': transaction.total_profit,
            'additional_cost': transaction.additional_cost,
            'payment_entries': [
                {
                    'id': UUID(str(pe.id)),
                    'transaction_id': UUID(str(pe.transaction_id)),
                    'payment_method_id': UUID(str(pe.payment_method_id)),
                    'value_paid': pe.value_paid,
                    'installments': pe.installments,
                    'is_bank_account': pe.is_bank_account
                }
                for pe in payment_entries_list
            ]
        }
        
        # Buscar nome do serviço para appointment
        apt_dict = AppointmentResponse.model_validate(appointment).model_dump()
        if appointment.service_id:
            service_id_str = str(appointment.service_id)
            service_query = select(Service).where(Service.id == service_id_str)
            service_result = await db.execute(service_query)
            service = service_result.scalar_one_or_none()
            if service:
                apt_dict['service_name'] = service.name
            else:
                apt_dict['service_name'] = None
        else:
            apt_dict['service_name'] = None
        
        response_message = "Agendamento finalizado com sucesso"
        if debtor:
            response_message = "Agendamento finalizado. Conta a receber criada."
        
        return FinalizeAppointmentResponse(
            transaction=TransactionResponse(**transaction_dict),
            appointment=apt_dict,
            message=response_message
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao finalizar agendamento: {str(e)}"
        )


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    status_code=200,
    summary="Cancelar agendamento",
    description="Cancela um agendamento com motivo obrigatório e envia notificação via WhatsApp para o cliente."
)
async def cancel_appointment(
    appointment_id: UUID = Path(..., description="UUID do agendamento"),
    cancel_data: AppointmentCancelRequest = ...,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Cancela um agendamento e envia notificação via WhatsApp.
    
    Esta rota:
    1. Valida o agendamento
    2. Atualiza status para CANCELED
    3. Armazena o motivo do cancelamento
    4. Envia notificação via WhatsApp para o cliente (em background)
    
    Args:
        appointment_id: UUID do agendamento
        cancel_data: Dados de cancelamento (cancellation_reason obrigatório)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        background_tasks: Background tasks para envio assíncrono de WhatsApp
        
    Returns:
        AppointmentResponse: Agendamento atualizado
        
    Raises:
        HTTPException 404: Se o agendamento não for encontrado
        HTTPException 400: Se o agendamento já estiver cancelado ou finalizado
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Converter IDs para strings
        tenant_id_str = str(tenant.id) if tenant.id else None
        appointment_id_str = str(appointment_id) if appointment_id else None
        
        if not tenant_id_str or not appointment_id_str:
            raise HTTPException(
                status_code=400,
                detail="IDs inválidos"
            )
        
        # Buscar agendamento
        appointment_query = select(Appointment).where(
            and_(
                Appointment.id == appointment_id_str,
                Appointment.tenant_id == tenant_id_str
            )
        )
        appointment_result = await db.execute(appointment_query)
        appointment = appointment_result.scalar_one_or_none()
        
        if not appointment:
            raise HTTPException(
                status_code=404,
                detail="Agendamento não encontrado"
            )
        
        # Validar que não está cancelado ou finalizado
        if appointment.status == AppointmentStatus.CANCELED:
            raise HTTPException(
                status_code=400,
                detail="Agendamento já está cancelado"
            )
        
        if appointment.status == AppointmentStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Não é possível cancelar um agendamento já finalizado"
            )
        
        # Atualizar agendamento
        appointment.status = AppointmentStatus.CANCELED
        appointment.cancellation_reason = cancel_data.cancellation_reason
        
        await db.commit()
        await db.refresh(appointment)
        
        # Enviar notificação via WhatsApp em background (se configurado)
        if tenant.whatsapp_phone_id and appointment.customer_phone and not appointment.is_manual_block:
            # Buscar nome do serviço para a mensagem
            service_name = "Serviço"
            if appointment.service_id:
                service_id_str = str(appointment.service_id)
                service_query = select(Service).where(Service.id == service_id_str)
                service_result = await db.execute(service_query)
                service = service_result.scalar_one_or_none()
                if service:
                    service_name = service.name
            
            # Formatar data/hora do agendamento
            appointment_datetime = appointment.start_datetime.strftime("%d/%m/%Y às %H:%M")
            
            # Adicionar task em background para enviar WhatsApp
            background_tasks.add_task(
                WhatsAppService.send_cancellation_notification,
                phone_number_id=tenant.whatsapp_phone_id,
                customer_phone=appointment.customer_phone,
                customer_name=appointment.customer_name or "Cliente",
                appointment_datetime=appointment_datetime,
                service_name=service_name,
                cancellation_reason=cancel_data.cancellation_reason
            )
        
        # Buscar nome do serviço para resposta
        apt_dict = AppointmentResponse.model_validate(appointment).model_dump()
        if appointment.service_id:
            service_id_str = str(appointment.service_id)
            service_query = select(Service).where(Service.id == service_id_str)
            service_result = await db.execute(service_query)
            service = service_result.scalar_one_or_none()
            if service:
                apt_dict['service_name'] = service.name
                apt_dict['service_display_color_code'] = service.display_color_code
            else:
                apt_dict['service_name'] = None
                apt_dict['service_display_color_code'] = None
        else:
            apt_dict['service_name'] = None
            apt_dict['service_display_color_code'] = None
        
        return AppointmentResponse(**apt_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao cancelar agendamento: {str(e)}"
        )


@router.put(
    "/{appointment_id}/reschedule",
    response_model=AppointmentResponse,
    status_code=200,
    summary="Reagendar agendamento",
    description=(
        "Reagenda um agendamento existente (manual ou via booking), "
        "validando disponibilidade e atualizando data/hora e serviço."
    )
)
async def reschedule_appointment(
    appointment_id: UUID = Path(..., description="UUID do agendamento"),
    reschedule_data: AppointmentRescheduleRequest = ...,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Reagenda um agendamento (manual ou via booking).

    Fluxo:
    1. Busca o agendamento e valida se pertence ao tenant
    2. Determina o serviço (novo ou o atual)
    3. Converte a nova data/hora para timezone-naive (UTC) para o banco
    4. Valida horário de funcionamento
    5. Verifica sobreposição com outros agendamentos (ignorando o próprio)
    6. Atualiza o agendamento e retorna o objeto atualizado
    """
    try:
        tenant_id_str = str(tenant.id) if tenant.id else None
        appointment_id_str = str(appointment_id) if appointment_id else None

        if not tenant_id_str or not appointment_id_str:
            raise HTTPException(
                status_code=400,
                detail="IDs inválidos"
            )

        # Buscar agendamento atual
        appointment_query = select(Appointment).where(
            and_(
                Appointment.id == appointment_id_str,
                Appointment.tenant_id == tenant_id_str
            )
        )
        appointment_result = await db.execute(appointment_query)
        appointment = appointment_result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(
                status_code=404,
                detail="Agendamento não encontrado"
            )

        # Não permitir reagendar cancelado ou finalizado
        if appointment.status == AppointmentStatus.CANCELED:
            raise HTTPException(
                status_code=400,
                detail="Não é possível reagendar um agendamento cancelado"
            )

        if appointment.status == AppointmentStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Não é possível reagendar um agendamento já finalizado"
            )

        # Carregar serviços atuais do agendamento
        await db.refresh(appointment, ['services'])
        current_service_ids = [str(s.id) for s in appointment.services] if appointment.services else []
        
        # Determinar serviços (novos ou atuais)
        if reschedule_data.service_ids:
            new_service_ids = [str(sid) for sid in reschedule_data.service_ids]
        elif current_service_ids:
            new_service_ids = current_service_ids
        else:
            raise HTTPException(
                status_code=400,
                detail="service_ids são obrigatórios para reagendamento"
            )
        
        # Calcular duração total dos novos serviços
        total_duration_minutes = await AppointmentService.calculate_total_duration(
            db_session=db,
            tenant_id=tenant.id,
            service_ids=[UUID(sid) for sid in new_service_ids]
        )
        
        # Processar nova data/hora
        # IMPORTANTE: O datetime vem do frontend em UTC (ISO string)
        # Precisamos converter para o horário local do Brasil antes de salvar
        # O MySQL armazena no horário local do servidor (Brasil)
        start_datetime_received = reschedule_data.data_agendamento
        
        # Se tem timezone, converter para horário local do Brasil
        if start_datetime_received.tzinfo is not None:
            try:
                from zoneinfo import ZoneInfo
            except ImportError:
                from backports.zoneinfo import ZoneInfo
            
            brazil_tz = ZoneInfo('America/Sao_Paulo')
            # Converter de UTC para horário do Brasil
            dt_brazil = start_datetime_received.astimezone(brazil_tz)
            # Remover timezone para salvar no MySQL (que está no horário local)
            start_datetime_utc = dt_brazil.replace(tzinfo=None)
        else:
            # Se não tem timezone, assumir que já está no horário local do Brasil
            start_datetime_utc = start_datetime_received

        # Calcular novo horário de fim baseado na duração total
        end_datetime_utc = AppointmentService.calculate_end_datetime(
            start_datetime_utc,
            total_duration_minutes
        )
        
        # Calcular valor total (atualizado com promoções na nova data)
        total_value = await AppointmentService.calculate_total_value(
            db_session=db,
            tenant_id=tenant.id,
            service_ids=[UUID(sid) for sid in new_service_ids],
            appointment_datetime=start_datetime_utc
        )

        # Validar horário de funcionamento (similar ao AvailabilityService.is_slot_available)
        target_date = start_datetime_utc.date()
        day_of_week = target_date.weekday()

        schedule_query = select(ScheduleConfig).where(
            and_(
                ScheduleConfig.tenant_id == tenant_id_str,
                ScheduleConfig.day_of_week == day_of_week
            )
        )
        schedule_result = await db.execute(schedule_query)
        schedule_config = schedule_result.scalar_one_or_none()

        if not schedule_config:
            raise HTTPException(
                status_code=400,
                detail=f"Configuração de horário não encontrada para o dia {day_of_week}"
            )

        if schedule_config.is_closed:
            raise HTTPException(
                status_code=400,
                detail="Estúdio fechado neste dia"
            )

        opening_time = schedule_config.start_time
        closing_time = schedule_config.end_time
        opening_datetime = datetime.combine(target_date, opening_time)
        closing_datetime = datetime.combine(target_date, closing_time)

        if start_datetime_utc < opening_datetime or end_datetime_utc > closing_datetime:
            raise HTTPException(
                status_code=400,
                detail="Horário fora do horário de funcionamento do estúdio"
            )

        # Verificar disponibilidade usando AvailabilityService
        is_available = await AvailabilityService.is_slot_available_with_duration(
            db_session=db,
            tenant_id=tenant.id,
            start_datetime=start_datetime_utc,
            total_duration_minutes=total_duration_minutes
        )
        
        # Mas também verificar manualmente excluindo o próprio agendamento
        conflicts_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id_str,
                Appointment.id != appointment_id_str,
                Appointment.start_datetime < end_datetime_utc,
                Appointment.end_datetime > start_datetime_utc,
                Appointment.status != AppointmentStatus.CANCELED
            )
        )
        conflicts_result = await db.execute(conflicts_query)
        conflicting_appointments = conflicts_result.scalars().all()

        if conflicting_appointments:
            raise HTTPException(
                status_code=400,
                detail="Este horário não está disponível. Por favor, escolha outro horário."
            )

        # Atualizar agendamento
        appointment.start_datetime = start_datetime_utc
        appointment.end_datetime = end_datetime_utc
        appointment.total_value = total_value
        
        # Atualizar service_id para compatibilidade (primeiro serviço)
        if new_service_ids:
            appointment.service_id = new_service_ids[0]
        
        # Remover serviços antigos da tabela intermediária
        from sqlalchemy import delete as sql_delete
        delete_stmt = sql_delete(AppointmentServiceModel).where(
            AppointmentServiceModel.appointment_id == appointment_id_str
        )
        await db.execute(delete_stmt)
        
        # Adicionar novos serviços na tabela intermediária
        for service_id_str in new_service_ids:
            appointment_service = AppointmentServiceModel(
                id=str(uuid.uuid4()),
                appointment_id=appointment_id_str,
                service_id=service_id_str
            )
            db.add(appointment_service)

        await db.commit()
        await db.refresh(appointment)

        return await build_appointment_response(appointment, db)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao reagendar agendamento: {str(e)}"
        )


@router.post(
    "/manual",
    response_model=AppointmentResponse,
    status_code=201,
    summary="Criar agendamento manual",
    description="Cria um novo agendamento manualmente pelo administrador. Valida disponibilidade e persiste com origem 'Manual'."
)
async def create_manual_appointment(
    appointment_data: ManualAppointmentCreate,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria um novo agendamento manual.
    
    Este endpoint permite que administradores criem agendamentos manualmente,
    validando a disponibilidade do horário e persistindo com a tag de origem "Manual".
    
    Fluxo:
    1. Recebe dados do agendamento (service_id, data_agendamento, cliente_nome, cliente_contato)
    2. Valida que o data_agendamento está em UTC (confia no valor recebido)
    3. Busca o serviço para obter duração
    4. Verifica disponibilidade do slot usando AvailabilityService
    5. Se disponível, cria o agendamento com description="Manual" (origem)
    6. Retorna o agendamento criado
    
    Args:
        appointment_data: Dados do agendamento manual (ManualAppointmentCreate)
        tenant: Tenant autenticado (injetado via dependency)
        db: Sessão do banco de dados (injetada)
        
    Returns:
        AppointmentResponse: Agendamento criado com status SCHEDULED
        
    Raises:
        HTTPException 400: Se os dados forem inválidos, serviço não existir ou horário indisponível
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Passo 1: Validar tenant_id
        tenant_id_str = str(tenant.id) if tenant.id else None
        if not tenant_id_str:
            raise HTTPException(
                status_code=400,
                detail="tenant_id inválido"
            )
        
        # Passo 2: Obter lista de service_ids (já normalizada pelo schema)
        service_ids = appointment_data.service_ids
        if not service_ids:
            raise HTTPException(
                status_code=400,
                detail="É necessário fornecer pelo menos um serviço"
            )
        
        # Passo 3: Calcular duração total e valor total
        total_duration_minutes = await AppointmentService.calculate_total_duration(
            db_session=db,
            tenant_id=tenant.id,
            service_ids=service_ids
        )
        
        # Passo 4: Processar data_agendamento
        # IMPORTANTE: O datetime vem do frontend em UTC (ISO string)
        # Precisamos converter para o horário local do Brasil antes de salvar
        # O MySQL armazena no horário local do servidor (Brasil)
        start_datetime_received = appointment_data.data_agendamento
        
        # Se tem timezone, converter para horário local do Brasil
        if start_datetime_received.tzinfo is not None:
            try:
                from zoneinfo import ZoneInfo
            except ImportError:
                from backports.zoneinfo import ZoneInfo
            
            brazil_tz = ZoneInfo('America/Sao_Paulo')
            # Converter de UTC para horário do Brasil
            dt_brazil = start_datetime_received.astimezone(brazil_tz)
            # Remover timezone para salvar no MySQL (que está no horário local)
            start_datetime_utc = dt_brazil.replace(tzinfo=None)
        else:
            # Se não tem timezone, assumir que já está no horário local do Brasil
            start_datetime_utc = start_datetime_received
        
        # Calcular valor total com promoções
        total_value = await AppointmentService.calculate_total_value(
            db_session=db,
            tenant_id=tenant.id,
            service_ids=service_ids,
            appointment_datetime=start_datetime_utc
        )
        
        # Passo 5: Calcular end_datetime baseado na duração total
        end_datetime_utc = AppointmentService.calculate_end_datetime(
            start_datetime_utc,
            total_duration_minutes
        )
        
        # Passo 6: Verificar disponibilidade do slot usando a duração total
        is_available = await AvailabilityService.is_slot_available_with_duration(
            db_session=db,
            tenant_id=tenant.id,
            start_datetime=start_datetime_utc,
            total_duration_minutes=total_duration_minutes
        )
        
        if not is_available:
            raise HTTPException(
                status_code=400,
                detail="Este horário não está disponível. Por favor, escolha outro horário."
            )
        
        # Passo 7: Buscar serviços para obter informações de exibição
        services = await AppointmentService.get_services_by_ids(
            db_session=db,
            tenant_id=tenant.id,
            service_ids=service_ids
        )
        
        # Passo 8: Lógica de UPSERT de Cliente (CRM)
        # Garantir unificação: usar a mesma tabela de clientes (aniversariantes)
        # Se client_id for fornecido, validar e usar. Caso contrário, buscar/criar/atualizar pelo telefone
        client_id_str = None
        
        if appointment_data.client_id:
            # Se client_id foi fornecido, validar que existe e pertence ao tenant
            client_query = select(Client).where(
                and_(
                    Client.id == str(appointment_data.client_id),
                    Client.tenant_id == tenant_id_str
                )
            )
            client_result = await db.execute(client_query)
            existing_client = client_result.scalar_one_or_none()
            
            if not existing_client:
                raise HTTPException(
                    status_code=404,
                    detail="Cliente não encontrado"
                )
            
            # Se client_id foi fornecido, também atualizar nome e aniversário se informados
            if appointment_data.cliente_nome:
                existing_client.name = appointment_data.cliente_nome
            if appointment_data.cliente_aniversario:
                existing_client.birth_date = appointment_data.cliente_aniversario
            
            client_id_str = str(existing_client.id)
        else:
            # Normalizar telefone para busca (remover caracteres não numéricos)
            phone_clean = ''.join(filter(str.isdigit, appointment_data.cliente_contato))
            
            # Buscar cliente existente pelo telefone (mesma tabela de aniversariantes)
            client_query = select(Client).where(
                and_(
                    Client.tenant_id == tenant_id_str,
                    Client.phone_number == phone_clean
                )
            )
            client_result = await db.execute(client_query)
            existing_client = client_result.scalar_one_or_none()
            
            if existing_client:
                # Cliente existe: ATUALIZAR nome e aniversário (upsert)
                existing_client.name = appointment_data.cliente_nome
                if appointment_data.cliente_aniversario:
                    existing_client.birth_date = appointment_data.cliente_aniversario
                client_id_str = str(existing_client.id)
            else:
                # Cliente não existe: CRIAR novo registro na mesma tabela
                new_client = Client(
                    tenant_id=tenant_id_str,
                    name=appointment_data.cliente_nome,
                    phone_number=phone_clean,
                    birth_date=appointment_data.cliente_aniversario
                )
                db.add(new_client)
                await db.flush()  # Flush para obter o ID
                client_id_str = str(new_client.id)
        
        # Passo 9: Criar o Appointment no banco de dados
        # IMPORTANTE: Converter UUIDs para strings (PostgreSQL armazena UUIDs como String(36))
        new_appointment = Appointment(
            tenant_id=tenant_id_str,
            service_id=str(service_ids[0]) if service_ids else None,  # Mantido para compatibilidade
            client_id=client_id_str,  # Vincular ao cliente (CRM)
            customer_name=appointment_data.cliente_nome,  # Mantido como fallback/histórico
            customer_phone=appointment_data.cliente_contato,  # Mantido como fallback/histórico
            start_datetime=start_datetime_utc,
            end_datetime=end_datetime_utc,
            status=AppointmentStatus.SCHEDULED,
            description="Manual",  # Marca origem como "Manual"
            total_value=total_value  # Valor total agendado
        )
        
        db.add(new_appointment)
        await db.flush()  # Flush para obter o ID do appointment
        
        # Passo 10: Criar registros na tabela intermediária appointment_services
        for service_id in service_ids:
            appointment_service = AppointmentServiceModel(
                id=str(uuid.uuid4()),
                appointment_id=new_appointment.id,
                service_id=str(service_id)
            )
            db.add(appointment_service)
        
        await db.commit()
        await db.refresh(new_appointment)
        
        # Passo 10: Carregar serviços relacionamentos
        await db.refresh(new_appointment, ['services'])
        
        # Passo 11: Construir resposta com informações dos serviços
        apt_dict = AppointmentResponse.model_validate(new_appointment).model_dump()
        
        # Informações para compatibilidade (primeiro serviço)
        if services:
            first_service = services[0]
            apt_dict['service_name'] = first_service.name
            apt_dict['service_display_color_code'] = first_service.display_color_code
            apt_dict['service_id'] = first_service.id  # Para compatibilidade
        
        # Lista de serviços
        apt_dict['service_ids'] = [str(s.id) for s in services]
        apt_dict['service_names'] = [s.name for s in services]
        apt_dict['service_display_color_codes'] = [s.display_color_code for s in services if s.display_color_code]
        apt_dict['total_value'] = float(total_value)
        
        return AppointmentResponse(**apt_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar agendamento manual: {str(e)}"
        )

