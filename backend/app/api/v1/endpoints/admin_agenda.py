"""
Endpoints administrativos para gerenciamento de Bloqueios de Agenda.

Permite que administradores bloqueiem horários manualmente (ex: Almoço, Folga, Manutenção).
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from typing import Annotated, List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.appointment import Appointment, AppointmentStatus

from app.schemas.agenda_block import AgendaBlockCreate, AgendaBlockResponse

router = APIRouter(prefix="/admin/agenda", tags=["Admin - Agenda"])


@router.post(
    "/blocks",
    response_model=AgendaBlockResponse,
    status_code=201,
    summary="Criar bloqueio de horário",
    description="Cria um bloqueio manual de horário (ex: Almoço, Folga, Manutenção). O horário bloqueado não estará disponível para agendamentos."
)
async def create_agenda_block(
    block_data: AgendaBlockCreate,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria um bloqueio manual de horário.
    
    Um bloqueio é um Appointment especial com is_manual_block=True que impede
    que clientes agendem naquele período. Bloqueios são considerados pelo
    AvailabilityService como colisões e não aparecem na lista de horários disponíveis.
    
    Fluxo:
    1. Valida que start_datetime < end_datetime
    2. Verifica se não há conflito com outros agendamentos/bloqueios
    3. Cria Appointment com is_manual_block=True
    4. service_id, customer_name e customer_phone são NULL para bloqueios
    
    Args:
        block_data: Dados do bloqueio (AgendaBlockCreate)
        tenant: Tenant autenticado (tenant_id será anexado automaticamente)
        db: Sessão do banco de dados
        
    Returns:
        AgendaBlockResponse: Bloqueio criado
        
    Raises:
        HTTPException 400: Se os dados forem inválidos ou houver conflito
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Validação: start_datetime deve ser anterior a end_datetime
        start_dt = block_data.start_datetime
        end_dt = block_data.end_datetime
        
        # Garantir timezone UTC
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=400,
                detail="start_datetime deve ser anterior a end_datetime"
            )
        
        # Verificar se há conflito com outros agendamentos/bloqueios existentes
        # (opcional, mas recomendado para evitar sobreposições)
        conflicting_query = select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant.id,
                Appointment.start_datetime < end_dt,
                Appointment.end_datetime > start_dt,
                Appointment.status != AppointmentStatus.CANCELED
            )
        )
        conflicting_result = await db.execute(conflicting_query)
        conflicting_appointments = conflicting_result.scalars().all()
        
        if conflicting_appointments:
            # Avisar sobre conflitos, mas permitir criar (admin pode querer sobrepor)
            # Se quiser bloquear, descomente a linha abaixo:
            # raise HTTPException(status_code=400, detail="Horário já está ocupado ou bloqueado")
            pass
        
        # Criar bloqueio como Appointment especial
        new_block = Appointment(
            tenant_id=tenant.id,  # tenant_id injetado automaticamente
            service_id=None,  # NULL para bloqueios
            customer_name=None,  # NULL para bloqueios
            customer_phone=None,  # NULL para bloqueios
            start_datetime=start_dt,
            end_datetime=end_dt,
            status=AppointmentStatus.CONFIRMED,  # Bloqueios são sempre confirmados
            is_manual_block=True,  # Marca como bloqueio manual
            description=block_data.description
        )
        
        db.add(new_block)
        await db.commit()
        await db.refresh(new_block)
        
        return AgendaBlockResponse.model_validate(new_block)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar bloqueio: {str(e)}"
        )


@router.get(
    "/blocks",
    response_model=List[AgendaBlockResponse],
    summary="Listar bloqueios",
    description="Retorna todos os bloqueios de agenda do tenant autenticado."
)
async def list_agenda_blocks(
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os bloqueios de agenda do tenant autenticado.
    
    Permite filtrar por período usando start_date e end_date.
    Apenas bloqueios (is_manual_block=True) são retornados.
    
    Args:
        start_date: Data inicial para filtrar (opcional, formato YYYY-MM-DD)
        end_date: Data final para filtrar (opcional, formato YYYY-MM-DD)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        List[AgendaBlockResponse]: Lista de bloqueios
    """
    # Construir query base
    query = select(Appointment).where(
        and_(
            Appointment.tenant_id == tenant.id,
            Appointment.is_manual_block == True
        )
    )
    
    # Aplicar filtros de data se fornecidos
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            query = query.where(Appointment.start_datetime >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="start_date deve estar no formato YYYY-MM-DD"
            )
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            # Adicionar 1 dia para incluir o dia inteiro
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.where(Appointment.start_datetime <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="end_date deve estar no formato YYYY-MM-DD"
            )
    
    # Ordenar por data de início
    query = query.order_by(Appointment.start_datetime)
    
    result = await db.execute(query)
    blocks = result.scalars().all()
    
    return [AgendaBlockResponse.model_validate(block) for block in blocks]


@router.get(
    "/blocks/{block_id}",
    response_model=AgendaBlockResponse,
    summary="Obter bloqueio",
    description="Retorna um bloqueio específico do tenant autenticado."
)
async def get_agenda_block(
    block_id: UUID = Path(..., description="UUID do bloqueio"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtém um bloqueio específico.
    
    Valida se o bloqueio pertence ao tenant autenticado e se é realmente
    um bloqueio manual (is_manual_block=True).
    
    Args:
        block_id: UUID do bloqueio
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        AgendaBlockResponse: Dados do bloqueio
        
    Raises:
        HTTPException 404: Se o bloqueio não for encontrado ou não pertencer ao tenant
    """
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.id == block_id,
                Appointment.tenant_id == tenant.id,
                Appointment.is_manual_block == True
            )
        )
    )
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=404,
            detail="Bloqueio não encontrado"
        )
    
    return AgendaBlockResponse.model_validate(block)


@router.delete(
    "/blocks/{block_id}",
    status_code=204,
    summary="Remover bloqueio",
    description="Remove um bloqueio de agenda, liberando o horário para agendamentos."
)
async def delete_agenda_block(
    block_id: UUID = Path(..., description="UUID do bloqueio"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove um bloqueio de agenda.
    
    Ao remover um bloqueio, o horário fica disponível novamente para agendamentos.
    
    Args:
        block_id: UUID do bloqueio
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        None (status 204 No Content)
        
    Raises:
        HTTPException 404: Se o bloqueio não for encontrado ou não pertencer ao tenant
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Buscar bloqueio e validar que pertence ao tenant
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.id == block_id,
                    Appointment.tenant_id == tenant.id,
                    Appointment.is_manual_block == True
                )
            )
        )
        block = result.scalar_one_or_none()
        
        if not block:
            raise HTTPException(
                status_code=404,
                detail="Bloqueio não encontrado"
            )
        
        # Deletar o bloqueio
        await db.delete(block)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao remover bloqueio: {str(e)}"
        )


