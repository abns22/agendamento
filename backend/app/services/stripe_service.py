"""
Serviço de Integração com Stripe.

Isola toda a comunicação com a API do Stripe para gerenciar assinaturas mensais
dos estúdios. Gerencia checkout sessions e billing portal.

IMPORTANTE: Nunca armazene customer_id no banco de dados, apenas
stripe_subscription_id e price_id (plano).
"""
import stripe
from typing import Optional
from uuid import UUID
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class StripeService:
    """
    Serviço responsável por todas as interações com a API do Stripe.
    
    Gerencia:
    - Criação de checkout sessions para assinaturas
    - Portal de billing para gerenciamento de pagamentos
    - Webhooks (será implementado em endpoint separado)
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Inicializa o serviço Stripe com a chave secreta.
        
        Args:
            secret_key: Chave secreta do Stripe. Se None, usa settings.STRIPE_SECRET_KEY
        """
        self.secret_key = secret_key or settings.STRIPE_SECRET_KEY
        
        if not self.secret_key:
            logger.warning("Stripe secret key não configurada. Funcionalidades do Stripe não estarão disponíveis.")
        else:
            stripe.api_key = self.secret_key
    
    def create_checkout_session(
        self,
        tenant_id: UUID,
        plan_price_id: str,
        success_url: str,
        cancel_url: str,
        customer_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None
    ) -> dict:
        """
        Cria uma sessão de checkout do Stripe para assinatura mensal.
        
        Este método cria uma URL de checkout onde o administrador do estúdio
        pode inserir seus dados de pagamento e iniciar a assinatura.
        
        Se customer_id não for fornecido, um novo Customer será criado no Stripe.
        
        Args:
            tenant_id: UUID do tenant (estúdio) que está assinando
            plan_price_id: ID do preço do plano no Stripe (ex: 'price_1234567890')
            success_url: URL de redirecionamento após pagamento bem-sucedido
            cancel_url: URL de redirecionamento se o usuário cancelar
            customer_id: ID do customer no Stripe (opcional, se já existe)
            customer_email: Email do administrador (obrigatório se customer_id não fornecido)
            customer_name: Nome do administrador (opcional)
            
        Returns:
            dict: Dados da sessão de checkout, incluindo 'url' para redirecionamento
                  Exemplo: {
                      'id': 'cs_test_...',
                      'url': 'https://checkout.stripe.com/...',
                      'subscription': 'sub_...' (após pagamento),
                      'customer_id': 'cus_...' (ID do customer)
                  }
        
        Raises:
            stripe.error.StripeError: Se houver erro na API do Stripe
            ValueError: Se a chave secreta não estiver configurada
        """
        if not self.secret_key:
            raise ValueError("Stripe secret key não configurada")
        
        try:
            logger.info(
                f"🔄 Iniciando criação de checkout session | "
                f"Tenant ID: {tenant_id} | "
                f"Price ID: {plan_price_id} | "
                f"Customer ID existente: {customer_id or 'N/A'} | "
                f"Customer Email: {customer_email or 'N/A'}"
            )
            
            # Obter ou criar customer
            stripe_customer_id = self.get_or_create_customer(
                customer_id=customer_id,
                email=customer_email,
                name=customer_name,
                metadata={'tenant_id': str(tenant_id)}
            )
            
            logger.info(
                f"✅ Customer obtido/criado | "
                f"Customer ID: {stripe_customer_id} | "
                f"Tenant ID: {tenant_id}"
            )
            
            # Criar sessão de checkout para assinatura
            checkout_session = stripe.checkout.Session.create(
                # Modo de assinatura (recurring)
                mode='subscription',
                
                # Customer ID (já criado ou existente)
                customer=stripe_customer_id,
                
                # Preço do plano (price_id)
                line_items=[
                    {
                        'price': plan_price_id,
                        'quantity': 1,
                    },
                ],
                
                # URLs de redirecionamento
                success_url=success_url,
                cancel_url=cancel_url,
                
                # Metadata para identificar o tenant após o webhook
                # Isso permite associar a assinatura ao tenant correto
                metadata={
                    'tenant_id': str(tenant_id),
                },
                
                # Permitir códigos promocionais
                allow_promotion_codes=True,
                
                # Configurações de assinatura
                subscription_data={
                    'metadata': {
                        'tenant_id': str(tenant_id),
                    }
                },
                
                # Configurações de pagamento
                payment_method_types=['card'],
                
                # Modo de cobrança (automático para assinaturas)
                billing_address_collection='auto',
            )
            
            logger.info(
                f"✅ CHECKOUT SESSION CRIADA NO STRIPE | "
                f"Session ID: {checkout_session.id} | "
                f"Tenant ID: {tenant_id} | "
                f"Customer ID: {stripe_customer_id} | "
                f"Subscription ID: {checkout_session.subscription or 'N/A (será criado após pagamento)'} | "
                f"URL: {checkout_session.url[:50]}..."
            )
            
            return {
                'id': checkout_session.id,
                'url': checkout_session.url,
                'subscription_id': checkout_session.subscription,  # Pode ser None até pagamento
                'customer_id': stripe_customer_id,  # ID do customer criado/recuperado
            }
            
        except stripe.error.StripeError as e:
            logger.error(
                f"❌ ERRO do Stripe ao criar checkout session | "
                f"Tenant ID: {tenant_id} | "
                f"Price ID: {plan_price_id} | "
                f"Customer ID: {customer_id or 'N/A'} | "
                f"Erro Stripe: {str(e)} | "
                f"Tipo: {type(e).__name__} | "
                f"Código: {getattr(e, 'code', 'N/A')}",
                exc_info=True
            )
            raise
    
    def manage_billing_portal(
        self,
        customer_id: str,
        return_url: str
    ) -> dict:
        """
        Gera uma URL para o portal de billing do Stripe.
        
        O portal de billing permite que o administrador do estúdio:
        - Atualize método de pagamento
        - Veja histórico de faturas
        - Cancele ou altere a assinatura
        - Baixe recibos
        
        IMPORTANTE: O customer_id deve ser obtido da subscription do Stripe,
        não armazenado no banco. Use get_customer_id_from_subscription()
        para obter o customer_id a partir do stripe_subscription_id.
        
        Args:
            customer_id: ID do customer no Stripe (obtido da subscription)
            return_url: URL de retorno após sair do portal
            
        Returns:
            dict: Dados da sessão do portal, incluindo 'url' para redirecionamento
                  Exemplo: {
                      'id': 'bps_...',
                      'url': 'https://billing.stripe.com/...'
                  }
        
        Raises:
            stripe.error.StripeError: Se houver erro na API do Stripe
            ValueError: Se a chave secreta não estiver configurada
        """
        if not self.secret_key:
            raise ValueError("Stripe secret key não configurada")
        
        try:
            # Criar sessão do portal de billing
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            
            logger.info(f"Portal de billing criado para customer {customer_id}: {portal_session.id}")
            
            return {
                'id': portal_session.id,
                'url': portal_session.url,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Erro ao criar portal de billing: {str(e)}")
            raise
    
    def get_customer_id_from_subscription(
        self,
        subscription_id: str
    ) -> Optional[str]:
        """
        Obtém o customer_id a partir do subscription_id.
        
        Como não armazenamos customer_id no banco, precisamos obtê-lo
        da subscription quando necessário (ex: para abrir o portal de billing).
        
        Args:
            subscription_id: ID da assinatura no Stripe (stripe_subscription_id)
            
        Returns:
            str: ID do customer no Stripe, ou None se não encontrado
        
        Raises:
            stripe.error.StripeError: Se houver erro na API do Stripe
        """
        if not self.secret_key:
            raise ValueError("Stripe secret key não configurada")
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription.customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Erro ao obter customer_id da subscription: {str(e)}")
            raise
    
    def get_subscription_status(
        self,
        subscription_id: str
    ) -> Optional[dict]:
        """
        Obtém o status atual de uma assinatura.
        
        Útil para verificar se a assinatura está ativa, cancelada, etc.
        
        Args:
            subscription_id: ID da assinatura no Stripe
            
        Returns:
            dict: Dados da assinatura, incluindo 'status', 'current_period_end', etc.
                  ou None se não encontrada
        """
        if not self.secret_key:
            raise ValueError("Stripe secret key não configurada")
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'customer': subscription.customer,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Erro ao obter status da subscription: {str(e)}")
            return None
    
    def get_or_create_customer(
        self,
        customer_id: Optional[str],
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Obtém um Customer existente ou cria um novo no Stripe.
        
        Se customer_id for fornecido, tenta recuperar o Customer.
        Se não existir ou não for fornecido, cria um novo Customer.
        
        Args:
            customer_id: ID do customer no Stripe (opcional, se já existe)
            email: Email do customer (obrigatório para criar novo)
            name: Nome do customer (opcional)
            metadata: Metadados adicionais para o customer (opcional)
            
        Returns:
            str: ID do customer no Stripe
            
        Raises:
            stripe.error.StripeError: Se houver erro na API do Stripe
            ValueError: Se a chave secreta não estiver configurada ou email não fornecido para novo customer
        """
        if not self.secret_key:
            raise ValueError("Stripe secret key não configurada")
        
        # Se customer_id foi fornecido, tentar recuperar
        if customer_id:
            logger.info(
                f"🔍 Tentando recuperar customer existente | "
                f"Customer ID: {customer_id}"
            )
            try:
                customer = stripe.Customer.retrieve(customer_id)
                logger.info(
                    f"✅ Customer existente recuperado | "
                    f"Customer ID: {customer.id} | "
                    f"Email: {customer.email or 'N/A'} | "
                    f"Nome: {customer.name or 'N/A'}"
                )
                return customer.id
            except stripe.error.StripeError as e:
                # Se o customer não existe, criar um novo
                logger.warning(
                    f"⚠️ Customer {customer_id} não encontrado no Stripe, criando novo | "
                    f"Erro: {str(e)} | "
                    f"Tipo: {type(e).__name__} | "
                    f"Email fornecido: {email or 'N/A'}"
                )
        
        # Criar novo customer
        if not email:
            logger.error(
                f"❌ ERRO: Email é obrigatório para criar um novo customer | "
                f"Customer ID fornecido: {customer_id or 'N/A'} | "
                f"Name: {name or 'N/A'}"
            )
            raise ValueError("Email é obrigatório para criar um novo customer")
        
        logger.info(
            f"🆕 Criando novo customer no Stripe | "
            f"Email: {email} | "
            f"Nome: {name or 'N/A'} | "
            f"Metadata: {metadata}"
        )
        
        try:
            customer_data = {
                'email': email,
            }
            
            if name:
                customer_data['name'] = name
            
            if metadata:
                customer_data['metadata'] = metadata
            
            customer = stripe.Customer.create(**customer_data)
            logger.info(
                f"✅ NOVO CUSTOMER CRIADO NO STRIPE | "
                f"Customer ID: {customer.id} | "
                f"Email: {customer.email} | "
                f"Nome: {customer.name or 'N/A'} | "
                f"Metadata: {customer.metadata}"
            )
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(
                f"❌ ERRO ao criar customer no Stripe | "
                f"Email: {email} | "
                f"Nome: {name or 'N/A'} | "
                f"Metadata: {metadata} | "
                f"Erro Stripe: {str(e)} | "
                f"Tipo: {type(e).__name__} | "
                f"Código: {getattr(e, 'code', 'N/A')}",
                exc_info=True
            )
            raise

