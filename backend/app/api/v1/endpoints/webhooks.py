"""
Endpoints de Webhooks para integrações externas.

Estes endpoints são públicos (sem autenticação) e recebem eventos
de serviços externos como Stripe e WhatsApp.
"""
from fastapi import APIRouter, HTTPException, Request, Header, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, Optional
from uuid import UUID
import stripe
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models.tenant import Tenant

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

logger = logging.getLogger(__name__)


@router.post(
    "/stripe",
    status_code=200,
    summary="Webhook do Stripe",
    description="Recebe eventos do Stripe sobre pagamentos e assinaturas. Rota pública sem autenticação."
)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Processa eventos do Stripe via webhook.
    
    Este endpoint é público e não requer autenticação, mas valida a assinatura
    do Stripe para garantir que o evento é genuíno.
    
    Fluxo:
    1. Recebe o corpo da requisição em formato raw (bytes)
    2. Recebe o header Stripe-Signature
    3. Verifica a assinatura usando STRIPE_WEBHOOK_SECRET
    4. Processa o evento conforme o tipo
    
    Eventos processados:
    - checkout.session.completed: Pagamento inicial concluído
    - customer.subscription.deleted: Assinatura cancelada
    - invoice.payment_succeeded: Renovação paga com sucesso
    - invoice.payment_failed: Pagamento falhou
    
    Args:
        request: Objeto Request do FastAPI (para acessar body raw)
        stripe_signature: Header Stripe-Signature com assinatura do evento
        db: Sessão do banco de dados
        
    Returns:
        JSONResponse: Status 200 se processado com sucesso
        
    Raises:
        HTTPException 400: Se a assinatura for inválida ou evento não reconhecido
        HTTPException 500: Erro interno do servidor
    """
    try:
        # Obter corpo da requisição em formato raw (bytes)
        body = await request.body()
        
        if not stripe_signature:
            logger.warning("Webhook recebido sem Stripe-Signature header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe-Signature header é obrigatório"
            )
        
        if not settings.STRIPE_WEBHOOK_SECRET:
            logger.error("STRIPE_WEBHOOK_SECRET não configurado")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuração de webhook não encontrada"
            )
        
        # Verificar assinatura do Stripe
        try:
            event = stripe.Webhook.construct_event(
                payload=body,
                sig_header=stripe_signature,
                secret=settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Erro ao processar payload do webhook: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload inválido"
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Assinatura do webhook inválida: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assinatura inválida"
            )
        
        # Processar evento conforme o tipo
        event_type = event['type']
        event_data = event['data']['object']
        
        logger.info(f"Processando evento Stripe: {event_type}")
        
        # Processar eventos usando match case (Python 3.10+) ou if/elif
        match event_type:
            case 'checkout.session.completed':
                await handle_checkout_session_completed(event_data, db)
            
            case 'customer.subscription.deleted':
                await handle_subscription_deleted(event_data, db)
            
            case 'invoice.payment_succeeded':
                await handle_invoice_payment_succeeded(event_data, db)
            
            case 'invoice.payment_failed':
                await handle_invoice_payment_failed(event_data, db)
            
            case _:
                # Evento não processado, mas não é erro
                logger.info(f"Evento {event_type} recebido mas não processado")
        
        # Retornar JSON vazio com status 200 OK para o Stripe
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar webhook do Stripe: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar webhook: {str(e)}"
        )


async def handle_checkout_session_completed(
    session_data: dict,
    db: AsyncSession
):
    """
    Processa evento checkout.session.completed.
    
    Quando o pagamento inicial é concluído, atualiza o tenant com:
    - stripe_subscription_id
    - is_active = True
    
    Args:
        session_data: Dados da sessão de checkout do Stripe
        db: Sessão do banco de dados
    """
    try:
        # Obter subscription_id da sessão
        subscription_id = session_data.get('subscription')
        
        if not subscription_id:
            logger.warning("Checkout session sem subscription_id")
            return
        
        # Obter tenant_id dos metadados
        metadata = session_data.get('metadata', {})
        tenant_id_str = metadata.get('tenant_id')
        
        if not tenant_id_str:
            logger.warning("Checkout session sem tenant_id nos metadados")
            return
        
        # Validar formato UUID (mas usar string para MySQL)
        try:
            UUID(tenant_id_str)  # Validar formato
        except ValueError:
            logger.error(f"tenant_id inválido: {tenant_id_str}")
            return
        
        # Buscar tenant (MySQL armazena UUIDs como String(36))
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id_str)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(f"Tenant não encontrado: {tenant_id_str}")
            return
        
        # Atualizar tenant
        tenant.stripe_subscription_id = subscription_id
        tenant.is_active = True
        
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Tenant {tenant_id_str} ativado com subscription {subscription_id}")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao processar checkout.session.completed: {str(e)}", exc_info=True)
        raise


async def handle_invoice_payment_succeeded(
    invoice_data: dict,
    db: AsyncSession
):
    """
    Processa evento invoice.payment_succeeded.
    
    Quando uma renovação é paga com sucesso, ativa o tenant se estava inativo.
    
    Args:
        invoice_data: Dados da invoice do Stripe
        db: Sessão do banco de dados
    """
    try:
        # Obter subscription_id da invoice
        subscription_id = invoice_data.get('subscription')
        
        if not subscription_id:
            logger.warning("Invoice sem subscription_id")
            return
        
        # Buscar tenant pelo subscription_id
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"Tenant não encontrado para subscription {subscription_id}")
            return
        
        # Ativar tenant se estava inativo
        if not tenant.is_active:
            tenant.is_active = True
            await db.commit()
            await db.refresh(tenant)
            logger.info(f"Tenant {tenant.id} reativado após pagamento bem-sucedido")
        else:
            logger.info(f"Tenant {tenant.id} já estava ativo")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao processar invoice.payment_succeeded: {str(e)}", exc_info=True)
        raise


async def handle_subscription_deleted(
    subscription_data: dict,
    db: AsyncSession
):
    """
    Processa evento customer.subscription.deleted.
    
    Quando o cliente cancela a assinatura, desativa o tenant.
    
    Args:
        subscription_data: Dados da subscription do Stripe
        db: Sessão do banco de dados
    """
    try:
        # Obter subscription_id
        subscription_id = subscription_data.get('id')
        
        if not subscription_id:
            logger.warning("Subscription deleted event sem subscription_id")
            return
        
        # Buscar tenant pelo subscription_id
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"Tenant não encontrado para subscription {subscription_id}")
            return
        
        # Desativar tenant (cliente cancelou)
        tenant.is_active = False
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Tenant {tenant.id} desativado devido a cancelamento de assinatura")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao processar customer.subscription.deleted: {str(e)}", exc_info=True)
        raise


async def handle_invoice_payment_failed(
    invoice_data: dict,
    db: AsyncSession
):
    """
    Processa evento invoice.payment_failed.
    
    Quando um pagamento falha, desativa o tenant.
    Pode iniciar um período de carência (implementação futura).
    
    Args:
        invoice_data: Dados da invoice do Stripe
        db: Sessão do banco de dados
    """
    try:
        # Obter subscription_id da invoice
        subscription_id = invoice_data.get('subscription')
        
        if not subscription_id:
            logger.warning("Invoice sem subscription_id")
            return
        
        # Buscar tenant pelo subscription_id
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"Tenant não encontrado para subscription {subscription_id}")
            return
        
        # Desativar tenant (pagamento falhou)
        tenant.is_active = False
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Tenant {tenant.id} desativado devido a falha no pagamento")
        
        # TODO: Implementar período de carência (grace period)
        # Por exemplo, dar alguns dias antes de desativar completamente
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao processar invoice.payment_failed: {str(e)}", exc_info=True)
        raise

