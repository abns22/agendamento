"""
Endpoints públicos para agendamento (booking).

Estes endpoints são acessíveis sem autenticação e permitem que clientes
vejam disponibilidade e criem agendamentos através do tenant_slug.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.service import Service
from app.models.appointment import Appointment, AppointmentStatus
from app.services.availability_service import AvailabilityService
from app.services.whatsapp_service import WhatsAppService

from app.schemas.public_booking import AvailableSlotsResponse
from app.schemas.appointment import AppointmentCreate, AppointmentResponse
from app.schemas.public_service import PublicServiceResponse
from app.services.promotion_service import PromotionService

router = APIRouter(prefix="/booking", tags=["Public Booking"])


async def get_tenant_by_slug(
    tenant_slug: str,
    db: AsyncSession
) -> Tenant:
    """
    Busca um tenant ativo pelo slug.
    
    Args:
        tenant_slug: Slug do tenant (ex: 'estudio-bella')
        db: Sessão do banco de dados
        
    Returns:
        Objeto Tenant se encontrado e ativo
        
    Raises:
        HTTPException: 404 se o tenant não existir ou não estiver ativo
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == tenant_slug,
            Tenant.is_active == True
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail=f"Estúdio '{tenant_slug}' não encontrado ou inativo"
        )
    
    return tenant


@router.get(
    "/{tenant_slug}/slots",
    response_model=AvailableSlotsResponse,
    summary="Buscar horários disponíveis",
    description="Retorna uma lista de horários disponíveis para agendamento de um serviço específico em uma data."
)
async def get_available_slots(
    tenant_slug: str = Path(..., description="Slug do tenant (ex: 'estudio-bella')"),
    service_id: UUID = Query(..., description="UUID do serviço"),
    date: str = Query(..., description="Data no formato YYYY-MM-DD", pattern=r'^\d{4}-\d{2}-\d{2}$'),
    db: AsyncSession = Depends(get_db)
):
    """
    Busca horários disponíveis para agendamento.
    
    Esta rota é pública e permite que clientes vejam os horários disponíveis
    para um serviço específico em uma data, identificando o estúdio pelo slug.
    
    Fluxo:
    1. Recebe o tenant_slug do path
    2. Busca o tenant_id correspondente ao slug
    3. Valida se o tenant existe e está ativo
    4. Chama o AvailabilityService para calcular os slots disponíveis
    5. Retorna a lista de horários disponíveis
    
    Args:
        tenant_slug: Slug único do tenant (ex: 'estudio-bella')
        service_id: UUID do serviço a ser agendado
        date: Data no formato YYYY-MM-DD
        db: Sessão do banco de dados (injetada)
        
    Returns:
        AvailableSlotsResponse: Objeto com tenant_slug, service_id, date e lista de slots
        
    Raises:
        HTTPException 404: Se o tenant não for encontrado
        HTTPException 400: Se a data for inválida ou o serviço não existir
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Passo 1: Buscar tenant pelo slug
        tenant = await get_tenant_by_slug(tenant_slug, db)
        
        # Passo 2: Chamar o AvailabilityService
        # O serviço já valida se o service_id existe e pertence ao tenant
        available_slots = await AvailabilityService.get_available_slots(
            db_session=db,
            tenant_id=tenant.id,
            service_id=service_id,
            date_str=date
        )
        
        # Passo 3: Retornar resposta formatada
        return AvailableSlotsResponse(
            tenant_slug=tenant_slug,
            service_id=service_id,
            date=date,
            available_slots=available_slots
        )
        
    except ValueError as e:
        # Erros de validação do AvailabilityService (data inválida, serviço não encontrado, etc)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTPExceptions (como 404 do get_tenant_by_slug)
        raise
    except Exception as e:
        # Erros inesperados
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar horários disponíveis: {str(e)}"
        )


@router.post(
    "/{tenant_slug}/appointments",
    response_model=AppointmentResponse,
    status_code=201,
    summary="Criar novo agendamento",
    description="Cria um novo agendamento para o cliente. Inclui verificação de concorrência e notificação via WhatsApp."
)
async def create_appointment(
    tenant_slug: str = Path(..., description="Slug do tenant (ex: 'estudio-bella')"),
    appointment_data: AppointmentCreate = ...,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria um novo agendamento.
    
    Esta rota pública permite que clientes criem agendamentos. Inclui:
    - Verificação de disponibilidade (prevenção de concorrência)
    - Criação do agendamento no banco de dados
    - Envio assíncrono de notificação via WhatsApp
    
    Fluxo:
    1. Recebe tenant_slug do path e AppointmentCreate no body
    2. Busca o tenant_id a partir do slug
    3. RE-VERIFICA disponibilidade do horário (prevenção de concorrência)
    4. Se não estiver livre, retorna 409 Conflict
    5. Busca o serviço para calcular end_datetime
    6. Cria o Appointment no banco
    7. Dispara Background Task para enviar notificação WhatsApp
    8. Retorna o agendamento criado
    
    Args:
        tenant_slug: Slug único do tenant
        appointment_data: Dados do agendamento (AppointmentCreate)
        background_tasks: Background tasks do FastAPI para processamento assíncrono
        db: Sessão do banco de dados (injetada)
        
    Returns:
        AppointmentResponse: Agendamento criado com status PENDING
        
    Raises:
        HTTPException 404: Se o tenant não for encontrado
        HTTPException 400: Se os dados forem inválidos ou serviço não existir
        HTTPException 409: Se o horário não estiver mais disponível (concorrência)
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Passo 1: Buscar tenant pelo slug (objeto completo para acessar dados de notificação)
        tenant = await get_tenant_by_slug(tenant_slug, db)
        # O objeto tenant contém:
        # - tenant.whatsapp_phone_id: ID do número WhatsApp Business na Meta API
        # - tenant.notification_phone_number: Número do estúdio para receber notificações
        
        # Passo 2: Buscar serviço para validar e calcular duração
        # IMPORTANTE: Converter service_id e tenant_id para strings (MySQL armazena UUIDs como String(36))
        service_id_str = str(appointment_data.service_id) if appointment_data.service_id else None
        tenant_id_str = str(tenant.id) if tenant.id else None
        
        if not service_id_str or not tenant_id_str:
            raise HTTPException(
                status_code=400,
                detail="service_id e tenant_id são obrigatórios"
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
                detail="Serviço não encontrado ou não pertence a este estúdio"
            )
        
        # Passo 3: RE-VERIFICAÇÃO CRÍTICA (Prevenção de Concorrência)
        # Garantir que o horário ainda está disponível antes de salvar
        # Isso evita que dois clientes agendem o mesmo slot simultaneamente
        start_datetime_utc = appointment_data.start_datetime
        if start_datetime_utc.tzinfo is not None:
            # Remover timezone se presente (timezone-naive para compatibilidade com PostgreSQL)
            start_datetime_utc = start_datetime_utc.replace(tzinfo=None)
        
        is_available = await AvailabilityService.is_slot_available(
            db_session=db,
            tenant_id=tenant.id,
            service_id=appointment_data.service_id,
            start_datetime=start_datetime_utc
        )
        
        if not is_available:
            raise HTTPException(
                status_code=409,
                detail="Este horário não está mais disponível. Por favor, escolha outro horário."
            )
        
        # Passo 4: Calcular end_datetime
        end_datetime_utc = start_datetime_utc + timedelta(minutes=service.duration_minutes)
        
        # Passo 5: Criar o Appointment no banco de dados
        # IMPORTANTE: Converter UUIDs para strings (PostgreSQL armazena UUIDs como String(36))
        tenant_id_str = str(tenant.id) if tenant.id else None
        service_id_str = str(appointment_data.service_id) if appointment_data.service_id else None
        
        new_appointment = Appointment(
            tenant_id=tenant_id_str,
            service_id=service_id_str,
            customer_name=appointment_data.customer_name,
            customer_phone=appointment_data.customer_phone,
            start_datetime=start_datetime_utc,
            end_datetime=end_datetime_utc,
            status=AppointmentStatus.PENDING
        )
        
        db.add(new_appointment)
        await db.commit()
        await db.refresh(new_appointment)
        
        # Passo 6: DUPLO DISPARO ASSÍNCRONO - Notificações WhatsApp em Background
        # As notificações são enfileiradas para envio imediato, permitindo resposta 200 OK sem atrasos
        
        # Formatar data e hora para exibição (usado em ambas as notificações)
        formatted_datetime = start_datetime_utc.strftime("%d/%m/%Y às %H:%M")
        
        # Tarefa 1: Notificar o CLIENTE sobre o agendamento
        # Usa template aprovado pela Meta (send_appointment_notification)
        if tenant.whatsapp_phone_id:
            background_tasks.add_task(
                send_whatsapp_notification_task,
                tenant_id=tenant.id,
                phone_number_id=tenant.whatsapp_phone_id,
                customer_phone=appointment_data.customer_phone,
                customer_name=appointment_data.customer_name,
                appointment_datetime=start_datetime_utc,
                service_name=service.name
            )
        
        # Tarefa 2: Notificar o ESTÚDIO sobre o novo agendamento
        # Usa mensagem de texto livre (send_new_appointment_alert)
        # Requisito: tenant.notification_phone_number e tenant.whatsapp_phone_id devem estar configurados
        if tenant.notification_phone_number and tenant.whatsapp_phone_id:
            background_tasks.add_task(
                send_studio_alert_task,
                phone_number_id=tenant.whatsapp_phone_id,
                tenant_phone_number=tenant.notification_phone_number,
                customer_name=appointment_data.customer_name,
                appointment_time=formatted_datetime,
                service_name=service.name
            )
        
        # Passo 7: Retornar o agendamento criado com nome do serviço
        apt_dict = AppointmentResponse.model_validate(new_appointment).model_dump()
        apt_dict['service_name'] = service.name  # Já temos o objeto service
        return AppointmentResponse(**apt_dict)
        
    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    except ValueError as e:
        # Erros de validação
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        # Erros inesperados
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar agendamento: {str(e)}"
        )


@router.get(
    "/{tenant_slug}/services",
    response_model=list[PublicServiceResponse],
    summary="Listar serviços públicos",
    description="Retorna todos os serviços ativos de um tenant (endpoint público para agendamento)."
)
async def get_public_services(
    tenant_slug: str = Path(..., description="Slug do tenant (ex: 'estudio-bella')"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista serviços disponíveis para agendamento público.
    
    Este endpoint é público e permite que clientes vejam os serviços
    oferecidos pelo estúdio antes de agendar.
    Inclui validação de promoções ativas.
    
    Args:
        tenant_slug: Slug único do tenant
        db: Sessão do banco de dados
        
    Returns:
        Lista de serviços do tenant com dados de promoção se ativa
        
    Raises:
        HTTPException 404: Se o tenant não for encontrado
    """
    try:
        # Buscar tenant pelo slug
        tenant = await get_tenant_by_slug(tenant_slug, db)
        
        # Buscar serviços do tenant
        services_query = select(Service).where(Service.tenant_id == tenant.id)
        services_result = await db.execute(services_query)
        services = services_result.scalars().all()
        
        # Processar serviços com validação de promoções
        result = []
        for service in services:
            # Verificar se promoção está ativa
            is_active, promotional_value = PromotionService.is_promotion_active(service)
            
            # Construir resposta
            service_dict = {
                "id": service.id,
                "name": service.name,
                "duration_minutes": service.duration_minutes,
                "price": service.price,
                "effective_price": Decimal(str(PromotionService.get_effective_price(service))),
                "is_promotional": service.is_promotional,
                "promotion_active": is_active,
                "promotional_value": Decimal(str(promotional_value)) if promotional_value else None,
                "promotion_display_name": service.promotion_display_name if is_active else None,
                "promotion_description": service.promotion_description if is_active else None,
                "promotion_color_code": service.promotion_color_code if is_active else None,
                "promotion_start_date": service.promotion_start_date if is_active else None,
                "promotion_end_date": service.promotion_end_date if is_active else None
            }
            
            result.append(PublicServiceResponse(**service_dict))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar serviços: {str(e)}"
        )


async def send_whatsapp_notification_task(
    tenant_id: UUID,
    phone_number_id: Optional[str],
    customer_phone: str,
    customer_name: str,
    appointment_datetime: datetime,
    service_name: str
):
    """
    Background task para enviar notificação WhatsApp.
    
    Esta função é executada de forma assíncrona após a criação do agendamento,
    permitindo que a resposta HTTP seja retornada imediatamente ao cliente.
    
    Args:
        tenant_id: UUID do tenant
        phone_number_id: ID do número de telefone do WhatsApp Business
        customer_phone: Telefone do cliente
        customer_name: Nome do cliente
        appointment_datetime: Data e hora do agendamento
        service_name: Nome do serviço
    """
    if not phone_number_id:
        # Se não houver phone_number_id configurado, apenas loga
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Notificação WhatsApp não enviada: phone_number_id não configurado para tenant {tenant_id}")
        return
    
    # Formatar data e hora para exibição
    formatted_datetime = appointment_datetime.strftime("%d/%m/%Y às %H:%M")
    
    # Enviar notificação
    await WhatsAppService.send_appointment_notification(
        phone_number_id=phone_number_id,
        customer_phone=customer_phone,
        customer_name=customer_name,
        appointment_datetime=formatted_datetime,
        service_name=service_name
    )


async def send_studio_alert_task(
    phone_number_id: str,
    tenant_phone_number: str,
    customer_name: str,
    appointment_time: str,
    service_name: str
):
    """
    Background task para enviar alerta de novo agendamento para o estúdio.
    
    Esta função é executada de forma assíncrona após a criação do agendamento
    para notificar o estúdio sobre o novo agendamento via WhatsApp.
    
    IMPORTANTE: O número de destino (tenant_phone_number) vem do objeto Tenant
    do banco de dados (o número que a empresa cadastrou para receber notificações).
    
    Args:
        phone_number_id: ID do número de telefone do WhatsApp Business (do Tenant)
        tenant_phone_number: Número de telefone do estúdio (formato internacional, ex: 5511999999999)
        customer_name: Nome do cliente que fez o agendamento
        appointment_time: Data e hora do agendamento formatada (ex: "25/12/2024 às 14:30")
        service_name: Nome do serviço agendado
    """
    if not phone_number_id or not tenant_phone_number:
        # Se não houver configuração, apenas loga
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Alerta para estúdio não enviado: configuração WhatsApp não encontrada")
        return
    
    # Enviar alerta para o estúdio
    await WhatsAppService.send_new_appointment_alert(
        phone_number_id=phone_number_id,
        tenant_phone_number=tenant_phone_number,
        customer_name=customer_name,
        appointment_time=appointment_time,
        service_name=service_name
    )

