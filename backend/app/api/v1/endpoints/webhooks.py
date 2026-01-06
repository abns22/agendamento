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
from datetime import datetime
import stripe
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models.tenant import Tenant

router = APIRouter(prefix="/payments", tags=["Webhooks"])

logger = logging.getLogger(__name__)


@router.post(
    "/webhook",
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
    - checkout.session.completed: Pagamento inicial concluído (atualiza subscription_status='active' e current_period_end)
    - invoice.paid: Renovação paga com sucesso (atualiza current_period_end)
    - invoice.payment_failed: Pagamento falhou (atualiza subscription_status='past_due')
    
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
        event_id = event.get('id', 'unknown')
        event_data = event['data']['object']
        
        # Log detalhado do evento recebido
        logger.info(
            f"💰 WEBHOOK RECEBIDO - Evento: {event_type} | "
            f"ID: {event_id} | "
            f"Timestamp: {datetime.utcnow().isoformat()} | "
            f"Objeto: {event_data.get('id', 'N/A') if isinstance(event_data, dict) else 'N/A'}"
        )
        
        # Processar eventos usando match case (Python 3.10+) ou if/elif
        match event_type:
            case 'checkout.session.completed':
                await handle_checkout_session_completed(event_data, db)
            
            case 'invoice.paid':
                await handle_invoice_paid(event_data, db)
            
            case 'invoice.payment_failed':
                await handle_invoice_payment_failed(event_data, db)
            
            case 'customer.subscription.deleted':
                await handle_subscription_deleted(event_data, db)
            
            case _:
                # Evento não processado, mas não é erro
                logger.info(
                    f"ℹ️ Evento {event_type} recebido mas não processado | "
                    f"Event ID: {event_id}"
                )
        
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
    - subscription_status = 'active'
    - current_period_end (da subscription)
    - stripe_customer_id (se disponível)
    
    Args:
        session_data: Dados da sessão de checkout do Stripe
        db: Sessão do banco de dados
    """
    session_id = session_data.get('id', 'unknown')
    customer_id = session_data.get('customer', 'unknown')
    amount_total = session_data.get('amount_total', 0)
    currency = session_data.get('currency', 'brl')
    
    logger.info(
        f"💳 CHECKOUT COMPLETED - Session: {session_id} | "
        f"Customer: {customer_id} | "
        f"Valor: {amount_total/100 if amount_total else 0} {currency.upper()}"
    )
    
    try:
        # Obter subscription_id da sessão
        subscription_id = session_data.get('subscription')
        
        if not subscription_id:
            logger.error(
                f"❌ ERRO: Checkout session {session_id} sem subscription_id | "
                f"Customer: {customer_id} | "
                f"Dados: {session_data}"
            )
            return
        
        # Obter tenant_id dos metadados
        metadata = session_data.get('metadata', {})
        tenant_id_str = metadata.get('tenant_id')
        
        if not tenant_id_str:
            logger.error(
                f"❌ ERRO: Checkout session {session_id} sem tenant_id nos metadados | "
                f"Subscription: {subscription_id} | "
                f"Customer: {customer_id} | "
                f"Metadata: {metadata}"
            )
            return
        
        # Validar formato UUID (mas usar string para MySQL)
        try:
            UUID(tenant_id_str)  # Validar formato
        except ValueError:
            logger.error(
                f"❌ ERRO: tenant_id inválido no checkout | "
                f"Session: {session_id} | "
                f"Subscription: {subscription_id} | "
                f"Tenant ID recebido: {tenant_id_str}"
            )
            return
        
        # Buscar tenant
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id_str)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(
                f"❌ ERRO: Tenant não encontrado no checkout | "
                f"Session: {session_id} | "
                f"Subscription: {subscription_id} | "
                f"Tenant ID: {tenant_id_str} | "
                f"Customer: {customer_id}"
            )
            return
        
        logger.info(
            f"✅ Tenant encontrado para checkout | "
            f"Tenant ID: {tenant_id_str} | "
            f"Subscription: {subscription_id} | "
            f"Session: {session_id}"
        )
        
        # Buscar dados da subscription no Stripe para obter current_period_end
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            customer_id_from_sub = subscription.customer
            subscription_status_stripe = subscription.status
            
            logger.info(
                f"📊 Subscription recuperada do Stripe | "
                f"Subscription: {subscription_id} | "
                f"Status: {subscription_status_stripe} | "
                f"Period End: {current_period_end} | "
                f"Customer: {customer_id_from_sub}"
            )
        except stripe.error.StripeError as e:
            logger.error(
                f"❌ ERRO ao buscar subscription no Stripe | "
                f"Subscription ID: {subscription_id} | "
                f"Tenant ID: {tenant_id_str} | "
                f"Session: {session_id} | "
                f"Erro: {str(e)} | "
                f"Tipo: {type(e).__name__}"
            )
            # Continuar mesmo sem os dados da subscription
            current_period_end = None
            customer_id_from_sub = session_data.get('customer')
        
        # Atualizar tenant
        old_subscription_id = tenant.stripe_subscription_id
        old_status = tenant.subscription_status
        old_customer_id = tenant.stripe_customer_id
        
        tenant.stripe_subscription_id = subscription_id
        tenant.subscription_status = 'active'
        if current_period_end:
            tenant.current_period_end = current_period_end
        if customer_id_from_sub and not tenant.stripe_customer_id:
            tenant.stripe_customer_id = customer_id_from_sub
        
        try:
            await db.commit()
            await db.refresh(tenant)
            
            logger.info(
                f"✅ CHECKOUT PROCESSADO COM SUCESSO | "
                f"Tenant ID: {tenant_id_str} | "
                f"Subscription: {subscription_id} (anterior: {old_subscription_id}) | "
                f"Status: active (anterior: {old_status}) | "
                f"Customer: {customer_id_from_sub} (anterior: {old_customer_id}) | "
                f"Period End: {current_period_end} | "
                f"Session: {session_id}"
            )
        except Exception as db_error:
            await db.rollback()
            logger.error(
                f"❌ ERRO ao salvar no banco após checkout | "
                f"Tenant ID: {tenant_id_str} | "
                f"Subscription: {subscription_id} | "
                f"Session: {session_id} | "
                f"Erro: {str(db_error)}",
                exc_info=True
            )
            raise
        
    except Exception as e:
        await db.rollback()
        logger.error(
            f"❌ ERRO CRÍTICO ao processar checkout.session.completed | "
            f"Session: {session_id} | "
            f"Subscription: {subscription_id if 'subscription_id' in locals() else 'N/A'} | "
            f"Tenant ID: {tenant_id_str if 'tenant_id_str' in locals() else 'N/A'} | "
            f"Erro: {str(e)} | "
            f"Tipo: {type(e).__name__}",
            exc_info=True
        )
        raise


async def handle_invoice_paid(
    invoice_data: dict,
    db: AsyncSession
):
    """
    Processa evento invoice.paid.
    
    Quando uma renovação é paga com sucesso, atualiza:
    - current_period_end (nova data do período)
    - subscription_status = 'active' (garantir que está ativo)
    
    Args:
        invoice_data: Dados da invoice do Stripe
        db: Sessão do banco de dados
    """
    invoice_id = invoice_data.get('id', 'unknown')
    amount_paid = invoice_data.get('amount_paid', 0)
    currency = invoice_data.get('currency', 'brl')
    customer_id = invoice_data.get('customer', 'unknown')
    
    logger.info(
        f"💵 INVOICE PAID - Invoice: {invoice_id} | "
        f"Customer: {customer_id} | "
        f"Valor: {amount_paid/100 if amount_paid else 0} {currency.upper()}"
    )
    
    try:
        # Obter subscription_id da invoice
        subscription_id = invoice_data.get('subscription')
        
        if not subscription_id:
            logger.error(
                f"❌ ERRO: Invoice {invoice_id} sem subscription_id | "
                f"Customer: {customer_id} | "
                f"Dados: {invoice_data}"
            )
            return
        
        # Buscar tenant pelo subscription_id
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"Tenant não encontrado para subscription {subscription_id}")
            return
        
        # Buscar dados da subscription no Stripe para obter current_period_end
        stripe.api_key = settings.STRIPE_SECRET_KEY
        old_period_end = tenant.current_period_end
        old_status = tenant.subscription_status
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            subscription_status_stripe = subscription.status
            
            logger.info(
                f"📊 Subscription recuperada para invoice paga | "
                f"Subscription: {subscription_id} | "
                f"Status: {subscription_status_stripe} | "
                f"Novo Period End: {current_period_end}"
            )
        except stripe.error.StripeError as e:
            logger.error(
                f"❌ ERRO ao buscar subscription no Stripe para invoice paga | "
                f"Subscription ID: {subscription_id} | "
                f"Tenant ID: {tenant.id} | "
                f"Invoice: {invoice_id} | "
                f"Erro: {str(e)} | "
                f"Tipo: {type(e).__name__}"
            )
            # Tentar usar period_end da invoice se disponível
            period_end = invoice_data.get('period_end')
            if period_end:
                current_period_end = datetime.fromtimestamp(period_end)
                logger.info(f"✅ Usando period_end da invoice: {current_period_end}")
            else:
                current_period_end = None
                logger.warning(f"⚠️ Period end não disponível nem na subscription nem na invoice")
        
        # Atualizar tenant
        tenant.subscription_status = 'active'
        if current_period_end:
            tenant.current_period_end = current_period_end
        
        try:
            await db.commit()
            await db.refresh(tenant)
            
            logger.info(
                f"✅ INVOICE PAID PROCESSADA COM SUCESSO | "
                f"Tenant ID: {tenant.id} | "
                f"Subscription: {subscription_id} | "
                f"Invoice: {invoice_id} | "
                f"Status: active (anterior: {old_status}) | "
                f"Period End: {current_period_end} (anterior: {old_period_end}) | "
                f"Valor: {amount_paid/100 if amount_paid else 0} {currency.upper()}"
            )
        except Exception as db_error:
            await db.rollback()
            logger.error(
                f"❌ ERRO ao salvar no banco após invoice paga | "
                f"Tenant ID: {tenant.id} | "
                f"Subscription: {subscription_id} | "
                f"Invoice: {invoice_id} | "
                f"Erro: {str(db_error)}",
                exc_info=True
            )
            raise
        
    except Exception as e:
        await db.rollback()
        logger.error(
            f"❌ ERRO CRÍTICO ao processar invoice.paid | "
            f"Invoice: {invoice_id} | "
            f"Subscription: {subscription_id if 'subscription_id' in locals() else 'N/A'} | "
            f"Tenant ID: {tenant.id if 'tenant' in locals() else 'N/A'} | "
            f"Erro: {str(e)} | "
            f"Tipo: {type(e).__name__}",
            exc_info=True
        )
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
    subscription_id = subscription_data.get('id', 'unknown')
    customer_id = subscription_data.get('customer', 'unknown')
    canceled_at = subscription_data.get('canceled_at')
    cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
    
    logger.warning(
        f"🗑️ SUBSCRIPTION DELETED - Subscription: {subscription_id} | "
        f"Customer: {customer_id} | "
        f"Cancel at period end: {cancel_at_period_end} | "
        f"Canceled at: {datetime.fromtimestamp(canceled_at) if canceled_at else 'N/A'}"
    )
    
    try:
        if not subscription_id:
            logger.error(
                f"❌ ERRO: Subscription deleted event sem subscription_id | "
                f"Customer: {customer_id} | "
                f"Dados: {subscription_data}"
            )
            return
        
        # Buscar tenant pelo subscription_id
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(
                f"❌ ERRO: Tenant não encontrado para subscription deletada | "
                f"Subscription: {subscription_id} | "
                f"Customer: {customer_id}"
            )
            return
        
        old_is_active = tenant.is_active
        
        # Desativar tenant (cliente cancelou)
        tenant.is_active = False
        
        try:
            await db.commit()
            await db.refresh(tenant)
            
            logger.warning(
                f"⚠️ SUBSCRIPTION DELETED PROCESSADA | "
                f"Tenant ID: {tenant.id} | "
                f"Subscription: {subscription_id} | "
                f"Customer: {customer_id} | "
                f"is_active: False (anterior: {old_is_active}) | "
                f"Cancel at period end: {cancel_at_period_end}"
            )
        except Exception as db_error:
            await db.rollback()
            logger.error(
                f"❌ ERRO ao desativar tenant após subscription deletada | "
                f"Tenant ID: {tenant.id} | "
                f"Subscription: {subscription_id} | "
                f"Erro: {str(db_error)}",
                exc_info=True
            )
            raise
        
    except Exception as e:
        await db.rollback()
        logger.error(
            f"❌ ERRO CRÍTICO ao processar customer.subscription.deleted | "
            f"Subscription: {subscription_id} | "
            f"Customer: {customer_id} | "
            f"Tenant ID: {tenant.id if 'tenant' in locals() else 'N/A'} | "
            f"Erro: {str(e)} | "
            f"Tipo: {type(e).__name__}",
            exc_info=True
        )
        raise


async def handle_invoice_payment_failed(
    invoice_data: dict,
    db: AsyncSession
):
    """
    Processa evento invoice.payment_failed.
    
    Quando um pagamento falha, atualiza:
    - subscription_status = 'past_due'
    
    O tenant ainda terá acesso durante o período de carência (3 dias após current_period_end)
    conforme implementado no middleware verify_subscription_access.
    
    Args:
        invoice_data: Dados da invoice do Stripe
        db: Sessão do banco de dados
    """
    invoice_id = invoice_data.get('id', 'unknown')
    amount_due = invoice_data.get('amount_due', 0)
    currency = invoice_data.get('currency', 'brl')
    customer_id = invoice_data.get('customer', 'unknown')
    attempt_count = invoice_data.get('attempt_count', 0)
    
    logger.warning(
        f"⚠️ INVOICE PAYMENT FAILED - Invoice: {invoice_id} | "
        f"Customer: {customer_id} | "
        f"Valor devido: {amount_due/100 if amount_due else 0} {currency.upper()} | "
        f"Tentativas: {attempt_count}"
    )
    
    try:
        # Obter subscription_id da invoice
        subscription_id = invoice_data.get('subscription')
        
        if not subscription_id:
            logger.error(
                f"❌ ERRO: Invoice {invoice_id} de pagamento falhado sem subscription_id | "
                f"Customer: {customer_id} | "
                f"Valor: {amount_due/100 if amount_due else 0} {currency.upper()} | "
                f"Dados: {invoice_data}"
            )
            return
        
        # Buscar tenant pelo subscription_id
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(
                f"❌ ERRO: Tenant não encontrado para invoice de pagamento falhado | "
                f"Invoice: {invoice_id} | "
                f"Subscription: {subscription_id} | "
                f"Customer: {customer_id} | "
                f"Valor: {amount_due/100 if amount_due else 0} {currency.upper()} | "
                f"Tentativas: {attempt_count}"
            )
            return
        
        old_status = tenant.subscription_status
        
        # Atualizar status para past_due (não desativar imediatamente)
        tenant.subscription_status = 'past_due'
        
        try:
            await db.commit()
            await db.refresh(tenant)
            
            logger.warning(
                f"⚠️ INVOICE PAYMENT FAILED PROCESSADA | "
                f"Tenant ID: {tenant.id} | "
                f"Subscription: {subscription_id} | "
                f"Invoice: {invoice_id} | "
                f"Status: past_due (anterior: {old_status}) | "
                f"Valor devido: {amount_due/100 if amount_due else 0} {currency.upper()} | "
                f"Tentativas: {attempt_count} | "
                f"Period End atual: {tenant.current_period_end}"
            )
        except Exception as db_error:
            await db.rollback()
            logger.error(
                f"❌ ERRO ao salvar status past_due no banco | "
                f"Tenant ID: {tenant.id} | "
                f"Subscription: {subscription_id} | "
                f"Invoice: {invoice_id} | "
                f"Erro: {str(db_error)}",
                exc_info=True
            )
            raise
        
    except Exception as e:
        await db.rollback()
        logger.error(
            f"❌ ERRO CRÍTICO ao processar invoice.payment_failed | "
            f"Invoice: {invoice_id} | "
            f"Subscription: {subscription_id if 'subscription_id' in locals() else 'N/A'} | "
            f"Tenant ID: {tenant.id if 'tenant' in locals() else 'N/A'} | "
            f"Valor: {amount_due/100 if amount_due else 0} {currency.upper()} | "
            f"Erro: {str(e)} | "
            f"Tipo: {type(e).__name__}",
            exc_info=True
        )
        raise

