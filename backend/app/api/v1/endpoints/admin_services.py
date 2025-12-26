"""
Endpoints administrativos para gerenciamento de Serviços (CRUD).

Estes endpoints requerem autenticação e garantem isolamento multi-tenant.
Apenas serviços do tenant autenticado podem ser acessados.
"""
from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Annotated, List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.models.service import Service

from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceResponse
from app.services.promotion_service import PromotionService

router = APIRouter(prefix="/admin/services", tags=["Admin - Services"])


@router.get(
    "",
    response_model=List[ServiceResponse],
    summary="Listar serviços",
    description="Retorna todos os serviços do tenant autenticado."
)
async def list_services(
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos os serviços do tenant autenticado.
    
    Apenas serviços que pertencem ao tenant_id injetado são retornados,
    garantindo isolamento multi-tenant.
    
    Args:
        tenant: Tenant autenticado (injetado via get_current_active_tenant)
        db: Sessão do banco de dados
        
    Returns:
        List[ServiceResponse]: Lista de serviços do tenant
    """
    # Converter tenant_id para string (PostgreSQL armazena UUIDs como String(36))
    tenant_id_str = str(tenant.id) if tenant.id else None
    
    if not tenant_id_str:
        raise HTTPException(
            status_code=400,
            detail="tenant_id inválido"
        )
    
    # Ordenar serviços: promoções primeiro (is_promotional DESC), depois por nome
    result = await db.execute(
        select(Service).where(
            Service.tenant_id == tenant_id_str
        ).order_by(
            Service.is_promotional.desc(),  # Promoções primeiro (True antes de False)
            Service.name.asc()  # Depois ordenar por nome alfabeticamente
        )
    )
    services = result.scalars().all()
    
    # Adicionar promotion_active calculado e ordenar resultado final
    services_with_promotion = []
    for service in services:
        # Calcular se promoção está ativa
        is_active, _ = PromotionService.is_promotion_active(service)
        # Converter para dict e adicionar promotion_active
        service_response = ServiceResponse.model_validate(service)
        service_dict = service_response.model_dump()
        service_dict['promotion_active'] = is_active
        services_with_promotion.append(service_dict)
    
    # Ordenar: promoções ativas primeiro, depois promoções inativas, depois não-promocionais
    services_with_promotion.sort(key=lambda x: (
        not x.get('promotion_active', False),  # False primeiro (promoções ativas)
        not x.get('is_promotional', False),  # Promoções primeiro
        x.get('name', '')  # Ordem alfabética
    ))
    
    # Retornar ServiceResponse com promotion_active incluído (usando model_validate que aceita campos extras)
    result = []
    for s in services_with_promotion:
        # Criar ServiceResponse a partir do dict (promotion_active é opcional no schema, então será aceito)
        result.append(ServiceResponse(**s))
    return result


@router.get(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Obter serviço",
    description="Retorna um serviço específico do tenant autenticado."
)
async def get_service(
    service_id: UUID = Path(..., description="UUID do serviço"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtém um serviço específico.
    
    Valida se o serviço pertence ao tenant autenticado antes de retornar.
    
    Args:
        service_id: UUID do serviço
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ServiceResponse: Dados do serviço
        
    Raises:
        HTTPException 404: Se o serviço não for encontrado ou não pertencer ao tenant
    """
    # Converter service_id para string (MySQL armazena UUIDs como String(36))
    service_id_str = str(service_id) if service_id else None
    tenant_id_str = str(tenant.id) if tenant.id else None
    
    if not service_id_str or not tenant_id_str:
        raise HTTPException(
            status_code=400,
            detail="service_id e tenant_id são obrigatórios"
        )
    
    result = await db.execute(
        select(Service).where(
            and_(
                Service.id == service_id_str,
                Service.tenant_id == tenant_id_str
            )
        )
    )
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(
            status_code=404,
            detail="Serviço não encontrado"
        )
    
    # Calcular promotion_active e retornar com esse campo
    is_active, _ = PromotionService.is_promotion_active(service)
    service_dict = ServiceResponse.model_validate(service).model_dump()
    service_dict['promotion_active'] = is_active
    
    # Retornar usando ServiceResponse(**service_dict) para incluir promotion_active
    return ServiceResponse(**service_dict)


@router.post(
    "",
    response_model=ServiceResponse,
    status_code=201,
    summary="Criar serviço",
    description="Cria um novo serviço para o tenant autenticado."
)
async def create_service(
    service_data: ServiceCreate,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria um novo serviço.
    
    O tenant_id é anexado automaticamente a partir do tenant autenticado,
    garantindo que o serviço seja criado para o tenant correto.
    
    Args:
        service_data: Dados do serviço (ServiceCreate)
        tenant: Tenant autenticado (tenant_id será anexado automaticamente)
        db: Sessão do banco de dados
        
    Returns:
        ServiceResponse: Serviço criado
        
    Raises:
        HTTPException 400: Se os dados forem inválidos
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Remover timezone das datas de promoção para compatibilidade com PostgreSQL
        promotion_start_date = service_data.promotion_start_date
        promotion_end_date = service_data.promotion_end_date
        if promotion_start_date is not None and hasattr(promotion_start_date, 'tzinfo') and promotion_start_date.tzinfo is not None:
            promotion_start_date = promotion_start_date.replace(tzinfo=None)
        if promotion_end_date is not None and hasattr(promotion_end_date, 'tzinfo') and promotion_end_date.tzinfo is not None:
            promotion_end_date = promotion_end_date.replace(tzinfo=None)
        
        # Criar novo serviço anexando o tenant_id automaticamente
        new_service = Service(
            tenant_id=tenant.id,  # tenant_id injetado automaticamente
            name=service_data.name,
            duration_minutes=service_data.duration_minutes,
            price=service_data.price,
            fixed_cost_value=service_data.fixed_cost_value,
            # Campos de promoção
            is_promotional=service_data.is_promotional or False,
            promotion_start_date=promotion_start_date,
            promotion_end_date=promotion_end_date,
            promotional_value=service_data.promotional_value,
            promotion_display_name=service_data.promotion_display_name,
            promotion_description=service_data.promotion_description,
            promotion_color_code=service_data.promotion_color_code
        )
        
        db.add(new_service)
        await db.commit()
        await db.refresh(new_service)
        
        return ServiceResponse.model_validate(new_service)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar serviço: {str(e)}"
        )


@router.put(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Atualizar serviço",
    description="Atualiza um serviço existente do tenant autenticado."
)
async def update_service(
    service_id: UUID = Path(..., description="UUID do serviço"),
    service_data: ServiceUpdate = ...,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza um serviço existente.
    
    Apenas serviços que pertencem ao tenant autenticado podem ser atualizados.
    Campos não fornecidos no ServiceUpdate não são alterados.
    
    Args:
        service_id: UUID do serviço
        service_data: Dados para atualização (ServiceUpdate - campos opcionais)
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        ServiceResponse: Serviço atualizado
        
    Raises:
        HTTPException 404: Se o serviço não for encontrado ou não pertencer ao tenant
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Converter service_id e tenant_id para string (PostgreSQL armazena UUIDs como String(36))
        service_id_str = str(service_id) if service_id else None
        tenant_id_str = str(tenant.id) if tenant.id else None
        
        if not service_id_str or not tenant_id_str:
            raise HTTPException(
                status_code=400,
                detail="service_id e tenant_id são obrigatórios"
            )
        
        # Buscar serviço e validar que pertence ao tenant
        result = await db.execute(
            select(Service).where(
                and_(
                    Service.id == service_id_str,
                    Service.tenant_id == tenant_id_str
                )
            )
        )
        service = result.scalar_one_or_none()
        
        if not service:
            raise HTTPException(
                status_code=404,
                detail="Serviço não encontrado"
            )
        
        # Atualizar apenas os campos fornecidos
        update_data = service_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Remover timezone das datas de promoção para compatibilidade com PostgreSQL
            if field in ('promotion_start_date', 'promotion_end_date') and value is not None:
                if hasattr(value, 'tzinfo') and value.tzinfo is not None:
                    value = value.replace(tzinfo=None)
            setattr(service, field, value)
        
        await db.commit()
        await db.refresh(service)
        
        return ServiceResponse.model_validate(service)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar serviço: {str(e)}"
        )


@router.delete(
    "/{service_id}",
    status_code=204,
    summary="Deletar serviço",
    description="Remove um serviço do tenant autenticado."
)
async def delete_service(
    service_id: UUID = Path(..., description="UUID do serviço"),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Deleta um serviço.
    
    Apenas serviços que pertencem ao tenant autenticado podem ser deletados.
    
    IMPORTANTE: Verificar se há agendamentos futuros associados a este serviço
    antes de permitir a exclusão (implementação futura).
    
    Args:
        service_id: UUID do serviço
        tenant: Tenant autenticado
        db: Sessão do banco de dados
        
    Returns:
        None (status 204 No Content)
        
    Raises:
        HTTPException 404: Se o serviço não for encontrado ou não pertencer ao tenant
        HTTPException 400: Se houver agendamentos futuros associados (futuro)
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Converter service_id e tenant_id para string (PostgreSQL armazena UUIDs como String(36))
        service_id_str = str(service_id) if service_id else None
        tenant_id_str = str(tenant.id) if tenant.id else None
        
        if not service_id_str or not tenant_id_str:
            raise HTTPException(
                status_code=400,
                detail="service_id e tenant_id são obrigatórios"
            )
        
        # Buscar serviço e validar que pertence ao tenant
        result = await db.execute(
            select(Service).where(
                and_(
                    Service.id == service_id_str,
                    Service.tenant_id == tenant_id_str
                )
            )
        )
        service = result.scalar_one_or_none()
        
        if not service:
            raise HTTPException(
                status_code=404,
                detail="Serviço não encontrado"
            )
        
        # TODO: Verificar se há agendamentos futuros associados a este serviço
        # Se houver, retornar erro 400 ao invés de deletar
        
        # Deletar o serviço
        await db.delete(service)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar serviço: {str(e)}"
        )

