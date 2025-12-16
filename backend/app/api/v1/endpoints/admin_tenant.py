"""
Endpoints administrativos para gerenciamento do Tenant (Estúdio).

Estes endpoints permitem que o administrador visualize e atualize
os dados do seu próprio tenant.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.schemas.tenant import TenantResponse, TenantUpdate

router = APIRouter(prefix="/admin/tenant", tags=["Admin - Tenant"])


@router.get(
    "",
    response_model=TenantResponse,
    summary="Obter dados do tenant atual",
    description="Retorna os dados do tenant do usuário autenticado."
)
async def get_current_tenant(
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna os dados do tenant do usuário autenticado.
    
    Esta rota é protegida e retorna apenas os dados do tenant
    ao qual o usuário autenticado pertence.
    
    Args:
        tenant: Tenant autenticado (injetado via get_current_active_tenant)
        db: Sessão do banco de dados
        
    Returns:
        TenantResponse: Dados do tenant
    """
    return TenantResponse.model_validate(tenant)


@router.put(
    "",
    response_model=TenantResponse,
    summary="Atualizar perfil do tenant",
    description="Atualiza os dados do tenant do usuário autenticado, incluindo configurações como notification_days."
)
async def update_tenant_profile(
    tenant_data: TenantUpdate,
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Atualiza os dados do tenant do usuário autenticado.
    
    Permite atualizar campos como:
    - notification_days: Número de dias para buscar agendamentos futuros
    - name, logo_url, description, address, phone_contact, schedule_display_text
    - whatsapp_phone_id, notification_phone_number
    
    Campos não fornecidos não são alterados (atualização parcial).
    
    Args:
        tenant_data: Dados para atualização (TenantUpdate - campos opcionais)
        tenant: Tenant autenticado (injetado via get_current_active_tenant)
        db: Sessão do banco de dados
        
    Returns:
        TenantResponse: Tenant atualizado
        
    Raises:
        HTTPException 400: Se os dados forem inválidos
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Atualizar apenas campos fornecidos (exclude_unset=True)
        update_data = tenant_data.model_dump(exclude_unset=True)
        
        # Não permitir atualizar slug via este endpoint (deve ser feito via super_admin)
        if 'slug' in update_data:
            del update_data['slug']
        
        # Não permitir atualizar is_active via este endpoint (deve ser feito via super_admin)
        if 'is_active' in update_data:
            del update_data['is_active']
        
        # Atualizar campos no objeto tenant
        for field, value in update_data.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)
        
        await db.commit()
        await db.refresh(tenant)
        
        return TenantResponse.model_validate(tenant)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar perfil do tenant: {str(e)}"
        )

