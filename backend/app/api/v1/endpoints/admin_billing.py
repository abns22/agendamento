"""
Endpoints administrativos para gerenciamento de Faturamento (Stripe).

Permite que administradores criem checkout sessions e gerenciem suas assinaturas.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.core.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.services.stripe_service import StripeService
from app.schemas.billing import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    ManageSubscriptionRequest,
    ManageSubscriptionResponse,
    BillingStatusResponse
)

router = APIRouter(prefix="/admin/billing", tags=["Admin - Billing"])


@router.get(
    "/status",
    response_model=BillingStatusResponse,
    summary="Obter status da assinatura",
    description="Retorna o status atual da assinatura do tenant do usuário autenticado."
)
async def get_billing_status(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna o status da assinatura do tenant do usuário autenticado.
    
    Verifica se o tenant possui uma assinatura ativa no Stripe e retorna
    informações sobre o status atual.
    
    Fluxo:
    1. Obtém o tenant do usuário autenticado
    2. Verifica se tem stripe_subscription_id
    3. Se tiver, consulta status no Stripe
    4. Retorna informações de status
    
    Args:
        current_user: Usuário autenticado (injetado via get_current_admin_user)
        db: Sessão do banco de dados
        
    Returns:
        BillingStatusResponse: Status da assinatura
        
    Raises:
        HTTPException 404: Se o tenant não for encontrado
    """
    try:
        # Obter tenant do usuário autenticado
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant não encontrado"
            )
        
        # Verificar se tenant está isento (prioridade máxima)
        is_exempt = tenant.is_exempt
        
        # Se estiver isento, considerar sempre ativo
        if is_exempt:
            return BillingStatusResponse(
                is_active=True,
                has_subscription=bool(tenant.stripe_subscription_id),
                subscription_id=tenant.stripe_subscription_id,
                subscription_status=tenant.subscription_status,
                current_period_end=None,  # Não relevante para isentos
                is_exempt=True
            )
        
        # Verificar se tem assinatura
        has_subscription = bool(tenant.stripe_subscription_id)
        is_active = tenant.is_active
        
        # Se tiver assinatura e Stripe configurado, buscar status detalhado
        subscription_status = tenant.subscription_status  # Usar status do banco como fallback
        current_period_end = None
        
        if has_subscription and settings.STRIPE_SECRET_KEY:
            try:
                stripe_service = StripeService()
                subscription_data = stripe_service.get_subscription_status(
                    tenant.stripe_subscription_id
                )
                
                if subscription_data:
                    subscription_status = subscription_data.get('status')
                    current_period_end = subscription_data.get('current_period_end')
                    # Atualizar is_active baseado no status do Stripe
                    is_active = subscription_status in ['active', 'trialing']
            except Exception as e:
                # Se houver erro ao consultar Stripe, usar status do banco
                logger.warning(f"Erro ao consultar status no Stripe: {str(e)}")
                # Usar current_period_end do banco se disponível
                if tenant.current_period_end:
                    import time
                    current_period_end = int(time.mktime(tenant.current_period_end.timetuple()))
        
        return BillingStatusResponse(
            is_active=is_active,
            has_subscription=has_subscription,
            subscription_id=tenant.stripe_subscription_id,
            subscription_status=subscription_status,
            current_period_end=current_period_end,
            is_exempt=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter status da assinatura: {str(e)}"
        )


@router.post(
    "/create-checkout-session",
    response_model=CreateCheckoutSessionResponse,
    summary="Criar sessão de checkout",
    description="Gera uma URL de checkout do Stripe para iniciar uma assinatura mensal."
)
async def create_checkout_session(
    request_data: CreateCheckoutSessionRequest = ...,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria uma sessão de checkout do Stripe para o tenant do usuário autenticado.
    
    Esta rota é protegida e requer autenticação JWT. O tenant_id é obtido
    automaticamente do usuário autenticado.
    
    Fluxo:
    1. Valida que o Stripe está configurado (STRIPE_SECRET_KEY e STRIPE_PRICE_ID)
    2. Obtém o tenant do usuário autenticado
    3. Cria checkout session via StripeService
    4. Retorna URL de redirecionamento
    
    Args:
        request_data: Dados da requisição (URLs de sucesso/cancelamento opcionais)
        current_user: Usuário autenticado (injetado via get_current_admin_user)
        db: Sessão do banco de dados
        
    Returns:
        CreateCheckoutSessionResponse: URL de checkout e ID da sessão
        
    Raises:
        HTTPException 400: Se o Stripe não estiver configurado
        HTTPException 500: Erro ao criar checkout session
    """
    # Validar configuração do Stripe
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe não está configurado. STRIPE_SECRET_KEY não encontrada."
        )
    
    if not settings.STRIPE_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe não está configurado. STRIPE_PRICE_ID não encontrado."
        )
    
    try:
        # Obter tenant do usuário autenticado
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant não encontrado"
            )
        
        # URLs padrão se não fornecidas
        # Priorizar domínio de produção (synkhro.com.br) se disponível
        frontend_url = "http://localhost:5173"  # Fallback padrão
        if settings.CORS_ORIGINS:
            # Buscar primeiro por domínio de produção
            production_url = next(
                (url for url in settings.CORS_ORIGINS if "synkhro.com.br" in url),
                None
            )
            if production_url:
                frontend_url = production_url
            else:
                # Se não encontrar, usar o primeiro da lista
                frontend_url = settings.CORS_ORIGINS[0] if isinstance(settings.CORS_ORIGINS, list) else str(settings.CORS_ORIGINS)
        
        success_url = request_data.success_url or f"{frontend_url}/admin/billing/success"
        cancel_url = request_data.cancel_url or f"{frontend_url}/admin/billing/cancel"
        
        # Criar instância do StripeService
        stripe_service = StripeService()
        
        # Criar checkout session
        # O StripeService irá criar ou recuperar o customer automaticamente
        checkout_data = stripe_service.create_checkout_session(
            tenant_id=UUID(tenant.id),
            plan_price_id=settings.STRIPE_PRICE_ID,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_id=tenant.stripe_customer_id,  # Passar customer_id se já existir
            customer_email=current_user.email,
            customer_name=tenant.name or current_user.email.split('@')[0]  # Usar nome do tenant ou email
        )
        
        # Salvar stripe_customer_id no banco se foi criado/recuperado
        if checkout_data.get('customer_id') and checkout_data['customer_id'] != tenant.stripe_customer_id:
            tenant.stripe_customer_id = checkout_data['customer_id']
            await db.commit()
            await db.refresh(tenant)
            logger.info(f"stripe_customer_id salvo para tenant {tenant.id}: {checkout_data['customer_id']}")
        
        return CreateCheckoutSessionResponse(
            checkout_url=checkout_data['url'],
            session_id=checkout_data['id']
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar checkout session: {str(e)}"
        )


@router.post(
    "/manage-subscription",
    response_model=ManageSubscriptionResponse,
    summary="Gerenciar assinatura",
    description="Gera uma URL para o portal de billing do Stripe, permitindo atualizar método de pagamento e ver histórico."
)
async def manage_subscription(
    request_data: ManageSubscriptionRequest = ...,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria uma sessão do portal de billing do Stripe para o tenant do usuário autenticado.
    
    Esta rota permite que o administrador:
    - Atualize método de pagamento
    - Veja histórico de faturas
    - Cancele ou altere a assinatura
    - Baixe recibos
    
    IMPORTANTE: O customer_id é obtido da subscription do Stripe, não armazenado no banco.
    
    Fluxo:
    1. Valida que o Stripe está configurado
    2. Obtém o tenant do usuário autenticado
    3. Verifica se o tenant tem stripe_subscription_id
    4. Obtém customer_id da subscription via StripeService
    5. Cria sessão do portal de billing
    6. Retorna URL de redirecionamento
    
    Args:
        request_data: Dados da requisição (URL de retorno opcional)
        current_user: Usuário autenticado (injetado via get_current_admin_user)
        db: Sessão do banco de dados
        
    Returns:
        ManageSubscriptionResponse: URL do portal e ID da sessão
        
    Raises:
        HTTPException 400: Se o Stripe não estiver configurado ou não houver assinatura
        HTTPException 404: Se o tenant não for encontrado
        HTTPException 500: Erro ao criar portal session
    """
    # Validar configuração do Stripe
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe não está configurado. STRIPE_SECRET_KEY não encontrada."
        )
    
    try:
        # Obter tenant do usuário autenticado
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant não encontrado"
            )
        
        # Verificar se o tenant tem assinatura
        if not tenant.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant não possui assinatura ativa. Crie uma assinatura primeiro."
            )
        
        # Criar instância do StripeService
        stripe_service = StripeService()
        
        # Obter customer_id da subscription
        customer_id = stripe_service.get_customer_id_from_subscription(
            tenant.stripe_subscription_id
        )
        
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível obter customer_id da assinatura. Verifique se a assinatura é válida."
            )
        
        # URL padrão se não fornecida
        # Priorizar domínio de produção (synkhro.com.br) se disponível
        frontend_url = "http://localhost:5173"  # Fallback padrão
        if settings.CORS_ORIGINS:
            # Buscar primeiro por domínio de produção
            production_url = next(
                (url for url in settings.CORS_ORIGINS if "synkhro.com.br" in url),
                None
            )
            if production_url:
                frontend_url = production_url
            else:
                # Se não encontrar, usar o primeiro da lista
                frontend_url = settings.CORS_ORIGINS[0] if isinstance(settings.CORS_ORIGINS, list) else str(settings.CORS_ORIGINS)
        
        return_url = request_data.return_url or f"{frontend_url}/admin/billing"
        
        # Criar sessão do portal de billing
        portal_data = stripe_service.manage_billing_portal(
            customer_id=customer_id,
            return_url=return_url
        )
        
        return ManageSubscriptionResponse(
            portal_url=portal_data['url'],
            session_id=portal_data['id']
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar portal de billing: {str(e)}"
        )

