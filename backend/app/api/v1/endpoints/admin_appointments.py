"""
Endpoints administrativos para gerenciamento de Agendamentos.

Permite que administradores visualizem e gerenciem agendamentos de clientes.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from app.models.payment_entry import PaymentEntry

from app.schemas.appointment import AppointmentResponse, AppointmentCancelRequest
from app.schemas.transaction import FinalizeAppointmentRequest, FinalizeAppointmentResponse, TransactionResponse
from app.services.finalization_service import FinalizationService
from app.services.whatsapp_service import WhatsAppService
from pydantic import BaseModel

router = APIRouter(prefix="/admin/appointments", tags=["Admin - Appointments"])


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
            # Converter data para datetime UTC (início e fim do dia)
            start_dt = datetime.strptime(date, '%Y-%m-%d').replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
            )
            end_dt = datetime.strptime(date, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
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
        
        # Construir resposta
        transaction_dict = TransactionResponse.model_validate(transaction).model_dump()
        transaction_dict['payment_entries'] = [
            {
                'id': str(pe.id),
                'transaction_id': str(pe.transaction_id),
                'payment_method_id': UUID(str(pe.payment_method_id)),
                'value_paid': pe.value_paid,
                'installments': pe.installments,
                'is_bank_account': pe.is_bank_account
            }
            for pe in payment_entries_list
        ]
        
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

