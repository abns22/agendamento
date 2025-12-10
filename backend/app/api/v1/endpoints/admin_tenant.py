"""
Endpoints administrativos para gerenciamento do Tenant (Estúdio).

Estes endpoints permitem que o administrador visualize e atualize
os dados do seu próprio tenant.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_tenant
from app.models.tenant import Tenant
from app.schemas.tenant import TenantResponse

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

