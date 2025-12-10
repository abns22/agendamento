"""
Endpoints públicos para dados do Tenant.

Estes endpoints são acessíveis sem autenticação e permitem que o frontend
público busque informações básicas do estúdio para personalização da página.
"""
from fastapi import APIRouter, HTTPException, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import get_db
from app.models.tenant import Tenant
from app.schemas.public_tenant import PublicTenantResponse

router = APIRouter(prefix="/public/tenant", tags=["Public - Tenant"])

logger = logging.getLogger(__name__)


@router.get(
    "/{tenant_slug}",
    response_model=PublicTenantResponse,
    summary="Obter dados públicos do tenant",
    description="Retorna os dados públicos do tenant para personalização da página de agendamento."
)
async def get_public_tenant(
    tenant_slug: str = Path(..., description="Slug do tenant (ex: 'estudio-bella')"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna os dados públicos do tenant identificado pelo slug.
    
    Esta rota é pública (sem autenticação) e retorna APENAS os dados
    que devem ser expostos na página de agendamento pública:
    - ID do tenant
    - Nome do estúdio
    - Slug
    - Logo URL
    - Descrição
    - Endereço
    - Telefone de contato
    - Horário de funcionamento (texto amigável)
    
    Dados sensíveis como whatsapp_phone_id, stripe_subscription_id,
    notification_phone_number NÃO são retornados.
    
    Args:
        tenant_slug: Slug único do tenant (ex: 'estudio-bella')
        db: Sessão do banco de dados (injetada)
        
    Returns:
        PublicTenantResponse: Dados públicos do tenant
        
    Raises:
        HTTPException 404: Se o tenant não for encontrado ou não estiver ativo
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Buscar tenant pelo slug (apenas ativos)
        result = await db.execute(
            select(Tenant).where(
                Tenant.slug == tenant_slug,
                Tenant.is_active == True
            )
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"Tentativa de acessar tenant inexistente ou inativo: '{tenant_slug}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Estúdio '{tenant_slug}' não encontrado ou inativo"
            )
        
        # Retornar apenas dados públicos
        return PublicTenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            logo_url=tenant.logo_url,
            description=tenant.description,
            address=tenant.address,
            phone_contact=tenant.phone_contact,
            schedule_display_text=tenant.schedule_display_text
        )
        
    except HTTPException:
        # Re-raise HTTPExceptions (404)
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar dados públicos do tenant '{tenant_slug}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar dados do estúdio: {str(e)}"
        )

