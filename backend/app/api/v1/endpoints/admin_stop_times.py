"""
Endpoints administrativos para gerenciamento de StopTimes (Intervalos de Parada/Almoço).

Estes endpoints requerem autenticação e garantem isolamento multi-tenant.
Apenas StopTimes do tenant autenticado podem ser acessados.
"""
from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Annotated, List

from app.core.database import get_db
from app.core.dependencies import verify_subscription_access
from app.models.tenant import Tenant
from app.models.stop_time import StopTime

from app.schemas.stop_time import StopTimeCreate, StopTimeUpdate, StopTimeResponse

router = APIRouter(prefix="/admin/stop-times", tags=["Admin - Stop Times"])


@router.get(
    "",
    response_model=List[StopTimeResponse],
    summary="Listar intervalos de parada",
    description="Retorna todos os intervalos de parada/almoço do tenant autenticado."
)
async def list_stop_times(
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os StopTimes do tenant autenticado.
    
    Apenas StopTimes que pertencem ao tenant_id injetado são retornados,
    garantindo isolamento multi-tenant.
    
    Args:
        tenant: Tenant autenticado (injetado via get_current_active_tenant)
        db: Sessão do banco de dados
        
    Returns:
        List[StopTimeResponse]: Lista de StopTimes do tenant
    """
    tenant_id_str = str(tenant.id)
    result = await db.execute(
        select(StopTime).where(StopTime.tenant_id == tenant_id_str).order_by(
            StopTime.day_of_week, StopTime.start_time
        )
    )
    stop_times = result.scalars().all()
    
    return [StopTimeResponse.model_validate(stop_time) for stop_time in stop_times]


@router.get(
    "/{stop_time_id}",
    response_model=StopTimeResponse,
    summary="Obter intervalo de parada",
    description="Retorna um intervalo de parada específico do tenant autenticado."
)
async def get_stop_time(
    stop_time_id: UUID = Path(..., description="UUID do intervalo de parada"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtém um StopTime específico do tenant autenticado.
    
    Args:
        stop_time_id: UUID do StopTime
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        StopTimeResponse: StopTime encontrado
        
    Raises:
        HTTPException 404: Se o StopTime não for encontrado ou não pertencer ao tenant
    """
    stop_time_id_str = str(stop_time_id)
    tenant_id_str = str(tenant.id)
    
    result = await db.execute(
        select(StopTime).where(
            and_(
                StopTime.id == stop_time_id_str,
                StopTime.tenant_id == tenant_id_str
            )
        )
    )
    stop_time = result.scalar_one_or_none()
    
    if not stop_time:
        raise HTTPException(
            status_code=404,
            detail="Intervalo de parada não encontrado ou não pertence a este estúdio"
        )
    
    return StopTimeResponse.model_validate(stop_time)


@router.post(
    "",
    response_model=StopTimeResponse,
    status_code=201,
    summary="Criar intervalo de parada",
    description="Cria um novo intervalo de parada/almoço para o tenant autenticado."
)
async def create_stop_time(
    stop_time_data: StopTimeCreate,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria um novo StopTime para o tenant autenticado.
    
    Args:
        stop_time_data: Dados do StopTime a ser criado
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        StopTimeResponse: StopTime criado
        
    Raises:
        HTTPException 400: Se os dados forem inválidos (ex: start_time >= end_time)
    """
    # Validar que start_time < end_time
    if stop_time_data.start_time >= stop_time_data.end_time:
        raise HTTPException(
            status_code=400,
            detail="O horário de início deve ser anterior ao horário de fim"
        )
    
    tenant_id_str = str(tenant.id)
    
    new_stop_time = StopTime(
        tenant_id=tenant_id_str,
        day_of_week=stop_time_data.day_of_week,
        start_time=stop_time_data.start_time,
        end_time=stop_time_data.end_time,
        description=stop_time_data.description
    )
    
    db.add(new_stop_time)
    await db.commit()
    await db.refresh(new_stop_time)
    
    return StopTimeResponse.model_validate(new_stop_time)


@router.put(
    "/{stop_time_id}",
    response_model=StopTimeResponse,
    summary="Atualizar intervalo de parada",
    description="Atualiza um intervalo de parada existente do tenant autenticado."
)
async def update_stop_time(
    stop_time_id: UUID = Path(..., description="UUID do intervalo de parada"),
    stop_time_data: StopTimeUpdate = ...,
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza um StopTime existente do tenant autenticado.
    
    Args:
        stop_time_id: UUID do StopTime
        stop_time_data: Dados atualizados do StopTime
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        StopTimeResponse: StopTime atualizado
        
    Raises:
        HTTPException 404: Se o StopTime não for encontrado ou não pertencer ao tenant
        HTTPException 400: Se os dados forem inválidos
    """
    stop_time_id_str = str(stop_time_id)
    tenant_id_str = str(tenant.id)
    
    result = await db.execute(
        select(StopTime).where(
            and_(
                StopTime.id == stop_time_id_str,
                StopTime.tenant_id == tenant_id_str
            )
        )
    )
    stop_time = result.scalar_one_or_none()
    
    if not stop_time:
        raise HTTPException(
            status_code=404,
            detail="Intervalo de parada não encontrado ou não pertence a este estúdio"
        )
    
    # Atualizar campos fornecidos
    update_data = stop_time_data.model_dump(exclude_unset=True)
    
    # Validar start_time < end_time se ambos forem fornecidos
    start_time = update_data.get('start_time', stop_time.start_time)
    end_time = update_data.get('end_time', stop_time.end_time)
    if start_time >= end_time:
        raise HTTPException(
            status_code=400,
            detail="O horário de início deve ser anterior ao horário de fim"
        )
    
    for field, value in update_data.items():
        setattr(stop_time, field, value)
    
    await db.commit()
    await db.refresh(stop_time)
    
    return StopTimeResponse.model_validate(stop_time)


@router.delete(
    "/{stop_time_id}",
    status_code=204,
    summary="Deletar intervalo de parada",
    description="Remove um intervalo de parada do tenant autenticado."
)
async def delete_stop_time(
    stop_time_id: UUID = Path(..., description="UUID do intervalo de parada"),
    tenant: Tenant = Depends(verify_subscription_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove um StopTime do tenant autenticado.
    
    Args:
        stop_time_id: UUID do StopTime
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Raises:
        HTTPException 404: Se o StopTime não for encontrado ou não pertencer ao tenant
    """
    stop_time_id_str = str(stop_time_id)
    tenant_id_str = str(tenant.id)
    
    result = await db.execute(
        select(StopTime).where(
            and_(
                StopTime.id == stop_time_id_str,
                StopTime.tenant_id == tenant_id_str
            )
        )
    )
    stop_time = result.scalar_one_or_none()
    
    if not stop_time:
        raise HTTPException(
            status_code=404,
            detail="Intervalo de parada não encontrado ou não pertence a este estúdio"
        )
    
    await db.delete(stop_time)
    await db.commit()
    
    return None

