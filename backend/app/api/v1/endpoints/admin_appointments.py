"""
Endpoints administrativos para gerenciamento de Agendamentos.

Permite que administradores visualizem e gerenciem agendamentos de clientes.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone, timedelta, date

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from app.models.payment_entry import PaymentEntry
from app.models.schedule_config import ScheduleConfig

from app.schemas.appointment import (
    AppointmentResponse,
    AppointmentCancelRequest,
    ManualAppointmentCreate,
    AppointmentRescheduleRequest
)
from app.schemas.transaction import FinalizeAppointmentRequest, FinalizeAppointmentResponse, TransactionResponse
from app.services.finalization_service import FinalizationService
from app.services.whatsapp_service import WhatsAppService
from app.services.availability_service import AvailabilityService
from pydantic import BaseModel
from datetime import timedelta

router = APIRouter(prefix="/admin/appointments", tags=["Admin - Appointments"])


@router.get(
    "/availability",
    response_model=dict,
    summary="Buscar disponibilidade geral",
    description="Retorna todos os horários disponíveis para uma data específica, usando a menor duração de serviço disponível."
)
async def get_availability(
    date: str = Query(..., description="Data no formato YYYY-MM-DD"),
    tenant: Tenant = Depends(get_current_active_tenant),
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
    tenant: Tenant = Depends(get_current_active_tenant),
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
    description="Retorna todos os agendamentos do tenant autenticado, opcionalmente filtrados por data, status e serviço. Sempre ordenado por start_datetime ASC."
)
async def list_appointments(
    date: Optional[str] = Query(None, description="Data para filtrar (YYYY-MM-DD). Se não fornecido, retorna todos os agendamentos."),
    status: Optional[str] = Query(None, description="Status para filtrar (SCHEDULED, CONFIRMED, COMPLETED, CANCELED)."),
    service_id: Optional[UUID] = Query(None, description="ID do serviço para filtrar."),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os agendamentos do tenant autenticado.
    
    Permite filtrar por data específica. Retorna tanto agendamentos de clientes
    quanto bloqueios manuais (is_manual_block=True).
    
    Args:
        date: Data para filtrar (opcional, formato YYYY-MM-DD)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[AppointmentResponse]: Lista de agendamentos ordenados por horário
    """
    # Construir query base
    # IMPORTANTE: Converter tenant_id para string (MySQL armazena UUIDs como String(36))
    tenant_id_str = str(tenant.id) if tenant.id else None
    if not tenant_id_str:
        raise HTTPException(
            status_code=400,
            detail="tenant_id inválido"
        )
    
    query = select(Appointment).where(
        Appointment.tenant_id == tenant_id_str
    )
    
    # Aplicar filtro de data se fornecido
    if date:
        try:
            # Converter data para datetime (início e fim do dia) - timezone-naive para compatibilidade com PostgreSQL
            start_dt = datetime.strptime(date, '%Y-%m-%d').replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_dt = datetime.strptime(date, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            
            # Filtrar agendamentos que começam no dia especificado
            query = query.where(
                and_(
                    Appointment.start_datetime >= start_dt,
                    Appointment.start_datetime <= end_dt
                )
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="date deve estar no formato YYYY-MM-DD"
            )
    
    # Aplicar filtro de status se fornecido
    if status:
        try:
            # Validar status
            status_enum = AppointmentStatus(status.upper())
            query = query.where(Appointment.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido. Use: SCHEDULED, CONFIRMED, COMPLETED, CANCELED"
            )
    
    # Aplicar filtro de service_id se fornecido
    if service_id:
        service_id_str = str(service_id)
        query = query.where(Appointment.service_id == service_id_str)
    
    # Ordenar por horário de início (ORDENAÇÃO OBRIGATÓRIA - ASC)
    query = query.order_by(Appointment.start_datetime.asc())
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    # Buscar nomes dos serviços para cada agendamento
    appointment_responses = []
    for apt in appointments:
        apt_dict = AppointmentResponse.model_validate(apt).model_dump()
        
        # Se tiver service_id, buscar o nome e display_color_code do serviço
        if apt.service_id:
            service_id_str = str(apt.service_id)
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
        
        appointment_responses.append(AppointmentResponse(**apt_dict))
    
    return appointment_responses


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Obter agendamento",
    description="Retorna um agendamento específico do tenant autenticado."
)
async def get_appointment(
    appointment_id: UUID = Path(..., description="UUID do agendamento"),
    tenant: Tenant = Depends(get_current_active_tenant),
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
    
    return AppointmentResponse.model_validate(appointment)


@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Atualizar agendamento",
    description="Atualiza um agendamento existente (status, horário, etc)."
)
async def update_appointment(
    appointment_id: UUID = Path(..., description="UUID do agendamento"),
    update_data: AppointmentUpdate = ...,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza o status de um agendamento.
    
    Args:
        appointment_id: UUID do agendamento
        update_data: Dados para atualização (AppointmentUpdate)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        AppointmentResponse: Agendamento atualizado
        
    Raises:
        HTTPException 404: Se o agendamento não for encontrado
        HTTPException 400: Se o status for inválido
    """
    # Buscar agendamento
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
    
    # Atualizar status se fornecido
    if update_data.status:
        try:
            appointment.status = AppointmentStatus(update_data.status.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido. Use: PENDING, CONFIRMED, CANCELED, COMPLETED"
            )
    
    await db.commit()
    await db.refresh(appointment)
    
    # Buscar nome do serviço se existir
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
    
    return AppointmentResponse(**apt_dict)


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
    tenant: Tenant = Depends(get_current_active_tenant),
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
    tenant: Tenant = Depends(get_current_active_tenant),
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
    tenant: Tenant = Depends(get_current_active_tenant),
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

        # Determinar serviço (novo ou atual)
        new_service_id = reschedule_data.service_id or appointment.service_id
        if not new_service_id:
            raise HTTPException(
                status_code=400,
                detail="service_id é obrigatório para reagendamento"
            )

        service_id_str = str(new_service_id)

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
                status_code=400,
                detail="Serviço não encontrado ou não pertence a este tenant"
            )

        # Processar nova data/hora (confiar que está em UTC)
        start_datetime_utc = reschedule_data.data_agendamento
        if start_datetime_utc.tzinfo is not None:
            start_datetime_utc = start_datetime_utc.replace(tzinfo=None)

        # Calcular novo horário de fim
        end_datetime_utc = start_datetime_utc + timedelta(minutes=service.duration_minutes)

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

        # Verificar sobreposição com outros agendamentos, ignorando o próprio agendamento
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
        appointment.service_id = service_id_str

        await db.commit()
        await db.refresh(appointment)

        # Montar resposta com nome e cor do serviço
        apt_dict = AppointmentResponse.model_validate(appointment).model_dump()
        apt_dict["service_name"] = service.name
        apt_dict["service_display_color_code"] = getattr(service, "display_color_code", None)

        return AppointmentResponse(**apt_dict)

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
    tenant: Tenant = Depends(get_current_active_tenant),
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
        
        # Passo 2: Buscar serviço para validar e calcular duração
        service_id_str = str(appointment_data.service_id) if appointment_data.service_id else None
        if not service_id_str:
            raise HTTPException(
                status_code=400,
                detail="service_id é obrigatório"
            )
        
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
                status_code=400,
                detail="Serviço não encontrado ou não pertence a este tenant"
            )
        
        # Passo 3: Processar data_agendamento (confiar que está em UTC)
        start_datetime_utc = appointment_data.data_agendamento
        
        # Remover timezone se presente (timezone-naive para compatibilidade com PostgreSQL)
        if start_datetime_utc.tzinfo is not None:
            start_datetime_utc = start_datetime_utc.replace(tzinfo=None)
        
        # Passo 4: Verificar disponibilidade do slot
        is_available = await AvailabilityService.is_slot_available(
            db_session=db,
            tenant_id=tenant.id,
            service_id=appointment_data.service_id,
            start_datetime=start_datetime_utc
        )
        
        if not is_available:
            raise HTTPException(
                status_code=400,
                detail="Este horário não está disponível. Por favor, escolha outro horário."
            )
        
        # Passo 5: Calcular end_datetime
        end_datetime_utc = start_datetime_utc + timedelta(minutes=service.duration_minutes)
        
        # Passo 6: Criar o Appointment no banco de dados
        # IMPORTANTE: Converter UUIDs para strings (PostgreSQL armazena UUIDs como String(36))
        new_appointment = Appointment(
            tenant_id=tenant_id_str,
            service_id=service_id_str,
            customer_name=appointment_data.cliente_nome,
            customer_phone=appointment_data.cliente_contato,
            start_datetime=start_datetime_utc,
            end_datetime=end_datetime_utc,
            status=AppointmentStatus.SCHEDULED,
            description="Manual"  # Marca origem como "Manual"
        )
        
        db.add(new_appointment)
        await db.commit()
        await db.refresh(new_appointment)
        
        # Passo 7: Retornar o agendamento criado com nome do serviço
        apt_dict = AppointmentResponse.model_validate(new_appointment).model_dump()
        apt_dict['service_name'] = service.name
        apt_dict['service_display_color_code'] = service.display_color_code
        
        return AppointmentResponse(**apt_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar agendamento manual: {str(e)}"
        )

