"""
Endpoints administrativos para configurações do Tenant (Estúdio).

Estes endpoints permitem que o administrador visualize e atualize
as configurações do seu próprio tenant (nome, horários, WhatsApp, etc.).
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import time
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user, verify_subscription_access
from app.models.tenant import Tenant
from app.models.schedule_config import ScheduleConfig
from app.models.user import User
from app.schemas.tenant_config import TenantConfigResponse, TenantConfigUpdate

router = APIRouter(prefix="/admin/config", tags=["Admin - Config"])

logger = logging.getLogger(__name__)


def format_slug_as_company_name(slug: str) -> str:
    """
    Formata o slug como nome da empresa.
    Ex: "estudio-bella" -> "Estúdio Bella"
    """
    if not slug:
        return "Meu Estúdio"
    
    return slug.replace('-', ' ').title()


@router.get(
    "",
    response_model=TenantConfigResponse,
    summary="Obter configurações do tenant",
    description="Retorna todas as configurações do tenant do usuário autenticado."
)
async def get_tenant_config(
    current_user: User = Depends(get_current_admin_user),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna as configurações do tenant do usuário autenticado.
    
    Inclui:
    - Dados básicos do tenant (ID, slug, nome formatado)
    - Número de WhatsApp para notificações
    - Horários de funcionamento padrão (da configuração de segunda-feira)
    
    Args:
        current_user: Usuário autenticado (injetado via get_current_admin_user)
        tenant: Tenant autenticado (injetado via verify_subscription_access)
        db: Sessão do banco de dados
        
    Returns:
        TenantConfigResponse: Configurações do tenant
    """
    try:
        # Formatar nome da empresa (usar campo name se existir, senão formatar do slug)
        company_name = tenant.name or format_slug_as_company_name(tenant.slug)
        
        # Buscar horário padrão (usar segunda-feira como referência)
        schedule_query = select(ScheduleConfig).where(
            ScheduleConfig.tenant_id == tenant.id,
            ScheduleConfig.day_of_week == 0  # Segunda-feira
        )
        schedule_result = await db.execute(schedule_query)
        schedule_config = schedule_result.scalar_one_or_none()
        
        # Extrair horários padrão
        default_start_time = None
        default_end_time = None
        
        if schedule_config and not schedule_config.is_closed:
            default_start_time = schedule_config.start_time.strftime('%H:%M')
            default_end_time = schedule_config.end_time.strftime('%H:%M')
        
        return TenantConfigResponse(
            tenant_id=tenant.id,
            slug=tenant.slug,
            company_name=company_name,
            notification_phone_number=tenant.notification_phone_number,
            whatsapp_phone_id=tenant.whatsapp_phone_id,
            name=tenant.name,
            logo_url=tenant.logo_url,
            description=tenant.description,
            address=tenant.address,
            phone_contact=tenant.phone_contact,
            schedule_display_text=tenant.schedule_display_text,
            default_start_time=default_start_time,
            default_end_time=default_end_time
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar configurações do tenant: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar configurações: {str(e)}"
        )


@router.put(
    "",
    response_model=TenantConfigResponse,
    summary="Atualizar configurações do tenant",
    description="Atualiza as configurações do tenant do usuário autenticado."
)
async def update_tenant_config(
    config_data: TenantConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza as configurações do tenant.
    
    IMPORTANTE: Buscamos o tenant novamente dentro da função para garantir
    que ele está na mesma sessão do banco de dados e será rastreado corretamente.
    
    Permite atualizar:
    - Número de WhatsApp para notificações
    - Horários de funcionamento padrão (atualiza todos os dias da semana)
    - Campos públicos: name, logo_url, description, address, phone_contact, schedule_display_text
    
    Args:
        config_data: Dados de configuração a serem atualizados (TenantConfigUpdate)
        current_user: Usuário autenticado (injetado via get_current_admin_user)
        db: Sessão do banco de dados
        
    Returns:
        TenantConfigResponse: Configurações atualizadas do tenant
        
    Raises:
        HTTPException 400: Se os dados forem inválidos
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Buscar tenant do usuário autenticado (garantir que está na mesma sessão)
        tenant_result = await db.execute(
            select(Tenant).where(
                Tenant.id == current_user.tenant_id,
                Tenant.is_active == True
            )
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant não encontrado ou inativo"
            )
        logger.info(
            f"Admin {current_user.email} (Tenant: {tenant.slug}) solicitou atualização de configurações. "
            f"Dados recebidos: {config_data.model_dump(exclude_unset=True)}"
        )
        
        # Atualizar número de WhatsApp se fornecido
        if config_data.notification_phone_number is not None:
            tenant.notification_phone_number = config_data.notification_phone_number
            logger.debug(f"Atualizado notification_phone_number: {config_data.notification_phone_number}")
        
        # Atualizar campos públicos se fornecidos
        if config_data.name is not None:
            tenant.name = config_data.name
            logger.debug(f"Atualizado name: {config_data.name}")
        
        if config_data.logo_url is not None:
            tenant.logo_url = config_data.logo_url
            logger.debug(f"Atualizado logo_url: {config_data.logo_url}")
        
        if config_data.description is not None:
            tenant.description = config_data.description
            logger.debug(f"Atualizado description: {config_data.description}")
        
        if config_data.address is not None:
            tenant.address = config_data.address
            logger.debug(f"Atualizado address: {config_data.address}")
        
        if config_data.phone_contact is not None:
            tenant.phone_contact = config_data.phone_contact
            logger.debug(f"Atualizado phone_contact: {config_data.phone_contact}")
        
        if config_data.schedule_display_text is not None:
            tenant.schedule_display_text = config_data.schedule_display_text
            logger.debug(f"Atualizado schedule_display_text: {config_data.schedule_display_text}")
        
        # Atualizar horários de funcionamento se fornecidos
        if config_data.default_start_time or config_data.default_end_time:
            # Validar que ambos os horários foram fornecidos
            if config_data.default_start_time and not config_data.default_end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="default_end_time é obrigatório quando default_start_time é fornecido"
                )
            if config_data.default_end_time and not config_data.default_start_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="default_start_time é obrigatório quando default_end_time é fornecido"
                )
            
            # Validar que start_time < end_time
            if config_data.default_start_time and config_data.default_end_time:
                start_time_obj = time.fromisoformat(config_data.default_start_time)
                end_time_obj = time.fromisoformat(config_data.default_end_time)
                
                if start_time_obj >= end_time_obj:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Horário de abertura deve ser anterior ao horário de fechamento"
                    )
                
                # Atualizar horários para todos os dias da semana (0-6)
                for day_of_week in range(7):
                    # Buscar configuração existente para este dia
                    schedule_query = select(ScheduleConfig).where(
                        ScheduleConfig.tenant_id == tenant.id,
                        ScheduleConfig.day_of_week == day_of_week
                    )
                    schedule_result = await db.execute(schedule_query)
                    schedule_config = schedule_result.scalar_one_or_none()
                    
                    if schedule_config:
                        # Atualizar configuração existente
                        schedule_config.start_time = start_time_obj
                        schedule_config.end_time = end_time_obj
                        schedule_config.is_closed = False
                    else:
                        # Criar nova configuração
                        new_schedule = ScheduleConfig(
                            tenant_id=tenant.id,
                            day_of_week=day_of_week,
                            start_time=start_time_obj,
                            end_time=end_time_obj,
                            is_closed=False
                        )
                        db.add(new_schedule)
                
                logger.info(
                    f"Admin {current_user.email} atualizou horários de funcionamento do tenant {tenant.slug}: "
                    f"{config_data.default_start_time} - {config_data.default_end_time}"
                )
        
        # Salvar alterações
        logger.info(f"Salvando alterações no banco de dados para tenant {tenant.slug}...")
        await db.commit()
        logger.info(f"Commit realizado com sucesso. Fazendo refresh do tenant...")
        await db.refresh(tenant)
        logger.info(
            f"Tenant atualizado: name={tenant.name}, logo_url={tenant.logo_url}, "
            f"description={tenant.description}, address={tenant.address}, "
            f"phone_contact={tenant.phone_contact}, schedule_display_text={tenant.schedule_display_text}"
        )
        
        # Retornar configurações atualizadas
        company_name = tenant.name or format_slug_as_company_name(tenant.slug)
        
        # Buscar horário atualizado
        schedule_query = select(ScheduleConfig).where(
            ScheduleConfig.tenant_id == tenant.id,
            ScheduleConfig.day_of_week == 0
        )
        schedule_result = await db.execute(schedule_query)
        schedule_config = schedule_result.scalar_one_or_none()
        
        default_start_time = None
        default_end_time = None
        
        if schedule_config and not schedule_config.is_closed:
            default_start_time = schedule_config.start_time.strftime('%H:%M')
            default_end_time = schedule_config.end_time.strftime('%H:%M')
        
        return TenantConfigResponse(
            tenant_id=tenant.id,
            slug=tenant.slug,
            company_name=company_name,
            notification_phone_number=tenant.notification_phone_number,
            whatsapp_phone_id=tenant.whatsapp_phone_id,
            name=tenant.name,
            logo_url=tenant.logo_url,
            description=tenant.description,
            address=tenant.address,
            phone_contact=tenant.phone_contact,
            schedule_display_text=tenant.schedule_display_text,
            default_start_time=default_start_time,
            default_end_time=default_end_time
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao atualizar configurações do tenant: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar configurações: {str(e)}"
        )

